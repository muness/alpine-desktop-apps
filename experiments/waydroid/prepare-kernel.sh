#!/bin/sh
# Materialize the pinned upstream recipe; never install or flash a device.
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../.." && pwd)
target=${1:-$root/out/waydroid/dc-1-pmos}
pin=9a69db8fffc851e3670647621e5e021f2039301b
[ ! -e "$target" ] || { echo "Refusing existing destination: $target" >&2; exit 1; }
git clone --no-checkout https://github.com/denysvitali/dc-1-pmos.git "$target"
git -C "$target" checkout --detach "$pin"
git -C "$target" apply --check "$here/kernel.patch" "$here/installer.patch"
git -C "$target" apply "$here/kernel.patch" "$here/installer.patch"
cp "$here/waydroid.config" "$target/pmaports/device/testing/linux-postmarketos-mediatek-mt6789/"
# Keep fallback modules separate from the candidate's module directory.
python3 - "$target/pmaports/device/testing/linux-postmarketos-mediatek-mt6789/APKBUILD" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
needle='\tmake ARCH="$_carch" LLVM=/usr/lib/llvm20/bin/ \\\n\t\tLD=/usr/bin/ld.lld HOSTLD=/usr/bin/ld.lld olddefconfig'
assert s.count(needle)==1
s=s.replace(needle, '\tscripts/config --set-str LOCALVERSION "-waydroid4"\n\tscripts/config --disable LOCALVERSION_AUTO\n'+needle)
p.write_text(s)
PY
printf 'Prepared %s\nBuild only: cd there and run sh scripts/kernel-local.sh build\n' "$target"
