from contextlib import ExitStack
from types import SimpleNamespace
import configparser
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('backend', Path(__file__).with_name('backend.py'))
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

class BackendTests(unittest.TestCase):
    def test_required_builtins_cannot_be_modules(self):
        self.assertEqual(b.missing_config({'CONFIG_BINDER':'m'}, {'CONFIG_BINDER':'y'}), ['CONFIG_BINDER'])
        self.assertEqual(b.missing_config({'CONFIG_LOOP':'y'}, {'CONFIG_LOOP':'m'}), [])

    def test_config_preserves_unrelated_values(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'waydroid.cfg'
            p.write_text('[waydroid]\nbinder=binder\n[properties]\ncustom.value=keep\n')
            b.configure(p)
            c=configparser.ConfigParser();c.read(p)
            self.assertEqual(c['properties']['custom.value'],'keep')
            self.assertEqual(c['properties']['dalvik.vm.extra-opts'],'-Xint')
            self.assertEqual(p.stat().st_mode & 0o777,0o644)

    def test_checksum_failure_never_installs_download(self):
        with tempfile.TemporaryDirectory() as d:
            pin={'filename':'system.zip','url':'https://example.invalid','size':3,'id':'0'*64,'romtype':'test'}
            with patch.object(b.urllib.request,'urlopen',return_value=io.BytesIO(b'bad')):
                with self.assertRaises(b.SetupError): b.download(pin,Path(d))
            self.assertFalse((Path(d)/'system.zip').exists())
            self.assertFalse((Path(d)/'system.partial').exists())

    def test_cached_verified_download_avoids_network(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'system.zip';p.write_bytes(b'good')
            pin={'filename':p.name,'size':4,'id':hashlib.sha256(b'good').hexdigest()}
            with patch.object(b.urllib.request,'urlopen',side_effect=AssertionError('network')):
                self.assertEqual(b.download(pin,Path(d)),p)

    def test_extract_does_not_traverse_or_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);z=root/'image.zip';out=root/'images'
            with zipfile.ZipFile(z,'w') as f:
                f.writestr('system.img',b'new');f.writestr('../escape',b'bad')
            b.extract_image(z,'system.img',out)
            self.assertEqual((out/'system.img').read_bytes(),b'new')
            self.assertFalse((root/'escape').exists())
            (out/'system.img').write_bytes(b'existing')
            with self.assertRaises(b.SetupError):b.extract_image(z,'system.img',out)
            self.assertEqual((out/'system.img').read_bytes(),b'existing')

    def test_existing_android_is_not_changed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cfg=root/'waydroid.cfg';cfg.write_text('existing')
            with patch.object(b,'STATE',root/'state'),patch.object(b,'CFG',cfg),patch.object(b,'preflight'),patch.object(b.os,'geteuid',return_value=0),patch.object(b,'run',side_effect=AssertionError('mutation')):
                with self.assertRaisesRegex(b.SetupError,'existing Android'):b.setup()
            self.assertEqual(cfg.read_text(),'existing')

    def test_command_failure_does_not_expose_output(self):
        result=b.subprocess.CompletedProcess(['apk'],1,stdout='private-user 192.168.1.1',stderr='secret')
        with patch.object(b.subprocess,'run',return_value=result):
            with self.assertRaises(b.SetupError) as caught:b.run(['apk','add','waydroid'])
        self.assertNotIn('secret',str(caught.exception));self.assertNotIn('private-user',str(caught.exception))

    def test_mount_guard_handles_descendants_and_escaped_spaces(self):
        self.assertTrue(b.mounted_under([Path('/home/test user')], '1 2 0:1 / /home/test\\040user/data rw - ext4 x rw'))
        self.assertFalse(b.mounted_under([Path('/var/lib/waydroid')], '1 2 0:1 / /var/lib/waydroid-other rw - ext4 x rw'))

    def test_remove_symlink_does_not_delete_target(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'keep';target.mkdir();(target/'data').write_text('keep')
            link=Path(d)/'link';link.symlink_to(target)
            b.remove_tree(link)
            self.assertTrue((target/'data').exists());self.assertFalse(link.exists())

    def test_variant_switch_refused_before_commands(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'variant').write_text('vanilla')
            with patch.object(b,'STATE',root),patch.object(b,'preflight'),patch.object(b.os,'geteuid',return_value=0),patch.object(b,'run',side_effect=AssertionError('mutation')):
                with self.assertRaisesRegex(b.SetupError,'another image choice'):b.setup('gapps')

    def test_remove_preserves_data_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            result=b.subprocess.CompletedProcess([],0,stdout='not-found\n')
            with patch.object(b,'STATE',root/'state'),patch.object(b,'MODULE_FILE',root/'modules'),patch.object(b,'NFT_LINK',root/'nft'),patch.object(b.os,'geteuid',return_value=0),patch.object(b,'mounted_under',return_value=False),patch.object(b.subprocess,'run',return_value=result),patch.object(b,'run',return_value=''),patch.object(b,'remove_tree',side_effect=AssertionError('data deletion')):
                b.remove(False)

    def test_active_mount_blocks_package_and_data_removal(self):
        with tempfile.TemporaryDirectory() as d:
            result=b.subprocess.CompletedProcess([],0,stdout='not-found\n')
            with patch.object(b,'STATE',Path(d)),patch.object(b.os,'geteuid',return_value=0),patch.object(b,'mounted_under',return_value=True),patch.object(b.subprocess,'run',return_value=result),patch.object(b,'run',side_effect=AssertionError('package mutation')),patch.object(b,'remove_tree',side_effect=AssertionError('data deletion')):
                with self.assertRaisesRegex(b.SetupError,'mounts are still active'):b.remove()

    def test_erasure_requires_identified_desktop_user(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(b,'STATE',Path(d)),patch.object(b.os,'geteuid',return_value=0),patch.dict(b.os.environ,{},clear=True),patch.object(b,'run',side_effect=AssertionError('mutation')):
                with self.assertRaisesRegex(b.SetupError,'desktop user'):b.remove(True)

    def test_new_install_selects_image_and_can_resume(self):
        for variant in ('vanilla', 'gapps'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                root=Path(d); cfg=root/'waydroid.cfg'
                for name,value in {'STATE':root/'state','CFG':cfg,'CACHE':root/'cache','IMAGES':root/'images','MODULE_FILE':root/'modules','NFT_LINK':root/'nft','HERE':Path(__file__).resolve().parents[1]}.items():
                    stack.enter_context(patch.object(b,name,value))
                stack.enter_context(patch.object(b.os,'geteuid',return_value=0))
                stack.enter_context(patch.object(b,'preflight'))
                stack.enter_context(patch.object(b.shutil,'disk_usage',return_value=SimpleNamespace(free=10*1024**3)))
                downloads=stack.enter_context(patch.object(b,'download',return_value=root/'archive'))
                stack.enter_context(patch.object(b,'extract_image'))
                def command(argv, *args):
                    if argv[:2]==['waydroid','init']:
                        cfg.write_text('[waydroid]\n')
                        self.assertEqual(argv[-1],variant.upper())
                    return ''
                commands=stack.enter_context(patch.object(b,'run',side_effect=command))
                b.setup(variant)
                self.assertTrue((root/'state/complete').exists())
                self.assertIn(variant.upper(),downloads.call_args_list[0].args[0]['filename'])
                calls=commands.call_count
                b.setup(variant)
                self.assertEqual(commands.call_count,calls)

    def test_erase_only_selects_android_paths(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            root=Path(d)
            for name,value in {'STATE':root/'state','CACHE':root/'cache','IMAGES':root/'images','MODULE_FILE':root/'modules','NFT_LINK':root/'nft'}.items():
                stack.enter_context(patch.object(b,name,value))
            stack.enter_context(patch.object(b.os,'geteuid',return_value=0))
            stack.enter_context(patch.dict(b.os.environ,{'PKEXEC_UID':'1000'}))
            stack.enter_context(patch.object(b.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir=str(root/'home'))))
            stack.enter_context(patch.object(b,'mounted_under',return_value=False))
            stack.enter_context(patch.object(b.subprocess,'run',return_value=b.subprocess.CompletedProcess([],0,stdout='not-found\n')))
            stack.enter_context(patch.object(b,'run',return_value=''))
            delete=stack.enter_context(patch.object(b,'remove_tree'))
            b.remove(True)
            self.assertEqual([c.args[0] for c in delete.call_args_list],[Path('/var/lib/waydroid'),root/'home/.local/share/waydroid',root/'cache'])

if __name__=='__main__':unittest.main()


