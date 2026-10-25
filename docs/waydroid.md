# Waydroid + experimental DC-1 kernel

This is one experiment: **a DC-1 kernel with the support Waydroid needs, plus
native Alpine Waydroid packages and verified Android images**. It does not use
this repository's glibc runtime. The kernel is specific to the Daylight DC-1;
no compatibility with other devices is claimed.

On one DC-1 running Nura edge, Android 13 booted, rendered through the Mali GPU,
loaded an HTTPS page, and accepted the Brydge keyboard after restarting its
session. GNOME and Tailscale remained usable. **Android currently needs
interpreter mode to avoid a system-server crash**, so startup and apps can be
slow. This is not a recommendation to replace the default kernel.

The source recipe is in [`experiments/waydroid`](../experiments/waydroid).
There are no kernel binaries or upstream PR for this experiment.

## What is pinned

| Component | Trial version |
| --- | --- |
| DC-1 packaging source | `denysvitali/dc-1-pmos` at `9a69db8fffc851e3670647621e5e021f2039301b` |
| Kernel source | `denysvitali/dc-1-linux-kernel` at `7cc767cd0cff39b77e252f26c9450d035c17b038` |
| Original kernel/packages | `7.2.0-rc5`, APK `7.2_rc5_git20260819-r67` |
| Trial kernel/packages | `7.2.0-rc5-waydroid4`, local APK `7.2_rc5_git20260819-r71` |
| Compiler | LLVM/Clang 20.1.8 |
| Waydroid | Alpine `1.6.3-r0`, with `waydroid-systemd` and `waydroid-nftrules` |
| Android system | VANILLA ARM64, Lineage 20 / Android 13, 20260927 |
| Android vendor | MAINLINE ARM64, 20261022 |

The fragment adds Binder/binderfs, ARM32 and legacy time-syscall compatibility,
POSIX message queues, loop/overlay/bridge/veth, policy routing and netfilter
support. The recipe checks resolved Kconfig values, including built-in versus
module requirements. Kernel and modules are separate APKs with an exact version
dependency. A unique kernel release keeps original and candidate modules apart.

## Build the kernel

Use native aarch64 Linux and the pinned upstream build prerequisites, including
pmbootstrap, Python, Git, Go and LLVM 20 inside its build environment. Allow
substantial disk space and build time. The upstream build script uses sudo for
its chroots; do not mechanically replace those calls with pkexec.

From this repository:

```sh
./experiments/waydroid/prepare-kernel.sh
cd out/waydroid/dc-1-pmos
sh scripts/kernel-local.sh build
```

Preparation refuses an existing destination. It checks out the exact upstream
commit, applies the kernel and installer patches, and adds the config fragment
and release suffix. It never flashes hardware. The build produces the kernel
and matching modules APKs under
`work/pmbootstrap-work/packages/edge/aarch64/`; public signing keys are under
`work/pmbootstrap-work/config_apk_keys/`. Keep private signing keys on the builder.

**Validation boundary:** the trial kernel was compiled and packaged in an
existing native Alpine container, reusing the original boot-proven DTBs.
This published wrapper prepares upstream's complete pmbootstrap recipe, which
also builds DTBs. Preparation and config regression tests pass; a fresh full
build and device installation using this wrapper have not been repeated.
Matching source/config does not imply byte-identical APKs. Do not substitute
these artifacts into an existing accepted transaction or reuse its checksum.

## Prepare recovery before installing

This is an operator-run procedure, not an unattended installer. Stay with the
tablet for the first boot. Start with a charged DC-1 on the original, proven
Linux kernel and working SSH. Save important data separately.

Copy the prepared source checkout, both APKs, public keys, and this repository's
`experiments/waydroid` directory to the tablet. Build the boot-image helper on
aarch64 Linux with `(cd boot/mkboot && go build -o mkboot .)` inside the prepared
checkout. Keep its executable in that checkout.

The guarded installer requires the installed `dc1-boot-sync` helper to match its
pinned source exactly. It also checks boot-image provenance, installed kernel
parity, APK signatures and availability of the original packages. **If a check
fails on another release, stop and reconcile that difference; do not bypass it.**

Record `uname -r` and `dc1-slotctl status`. Run the supplied recovery preparation
script as root (use absolute paths with graphical polkit):

```sh
pkexec /absolute/path/experiments/waydroid/arm-recovery.sh
```

It backs up the original module tree, pauses automatic updates, installs a
confirmation gate, and enables a ten-minute timer for the candidate kernel.
It refuses a pending or previously accepted experiment. This trial assumes the
original Linux slot remains intact; never write preloader, lk, dtbo or
vendor_boot partitions.

Stage with the prepared checkout's guarded installer. Replace the paths below:

```sh
pkexec /usr/bin/python3 /absolute/path/dc-1-pmos/scripts/kernel-local-install.py \
  install /absolute/path/dc-1-pmos \
  /absolute/path/apks/linux-postmarketos-mediatek-mt6789-7.2_rc5_git20260819-r71.apk \
  /absolute/path/public-keys
```

The modules APK must sit beside the kernel APK. The installer backs up both
boot slots and original APKs under `/var/lib/dc1/local-kernel/`, verifies the new
image by readback, and arms the inactive slot for one attempt. Its local patches
handle whitespace in slot status and an inactive Android image without a
dtbswap payload; the active Linux image and candidate still undergo validation.

Before rebooting, restore original modules alongside the candidate modules:

```sh
pkexec /usr/bin/tar -xf /var/lib/dc1/waydroid-test/rollback/modules.tar -C /
```

Verify both module directories exist, `pending.json` exists under
`/var/lib/dc1/local-kernel`, the confirmation service uses `confirm-gate.py`,
and `dc1-waydroid-recovery.timer` is enabled. Then reboot. The candidate is
`7.2.0-rc5-waydroid4`. **Do not mark the slot successful yourself.**

If testing is unfinished, let the ten-minute timer reboot to the proven slot.
A kernel that cannot reach userspace relies on the bootloader/watchdog fallback,
not the userspace timer. Following fallback, confirm the original kernel,
matching packages, GNOME and input work; automatic updates remain paused for
review. The trial exercised both the timed fallback and restoration of r67.

## Android userspace

Download the pinned official images before the timed test:

```sh
python3 experiments/waydroid/fetch-images.py out/waydroid/images
```

The downloader verifies size and SHA256 against the saved official OTA records
in `images.json`. Copy the verified ZIPs to the tablet. Install the native
`waydroid`, `waydroid-systemd`, `waydroid-nftrules` and `unzip` packages using APK.
Mask `waydroid-container.service` until the candidate kernel is running.
Extract the two ZIPs into `/usr/share/waydroid-extra/images` as root. Do not
replace images or reinitialize an existing Android installation without a
separate backup of its configuration and userdata.

On the candidate kernel, initialize with `waydroid init -s VANILLA` as root.
It should use the preinstalled images. In `/var/lib/waydroid/waydroid.cfg`, add
these entries to its existing `[properties]` section:

```ini
dalvik.vm.extra-opts = -Xint
dalvik.vm.usejit = false
```

Keep the config readable by the desktop user (`chmod 644`); a mode600 config
caused a Binder helper error in our trial. Run `waydroid upgrade -o` as root to
regenerate the configuration without fetching images.

Enable the packaged Waydroid nftables include by linking
`/usr/share/nftables.avail/51_waydroid.nft` into `/etc/nftables.d/51_waydroid.nft`.
Validate with `nft -c -f` and load the file with `nft -f` if those rules are not
already present. Review interaction with your existing firewall; do not flush
its rules. Load `iptable_filter`, `iptable_nat`, `iptable_mangle`, `iptable_raw`
and the corresponding `ip6table_*` modules. Unmask and start
`waydroid-container.service`.

As the logged-in Wayland desktop user, run:

```sh
waydroid show-full-ui
```

Allow roughly two minutes for interpreter-mode startup. Keep GNOME as your
normal desktop. To avoid starting Android at every login, put this override in
`~/.config/autostart/waydroid-session.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Waydroid Session
Hidden=true
```

## Test, then accept

Before the deadline, check GNOME, Wi-Fi, your keyboard/trackpad and Android.
As root, check `waydroid shell getprop sys.boot_completed` returns `1`; test
Android DNS and an HTTPS page, and check
`waydroid shell -- dumpsys SurfaceFlinger` for the GPU renderer. On the trial
it reported Mali-G57 MC2 / Panfrost / Mesa 26.0.8. Test touch and typing in an
Android text field. Check host browsing and any VPN as well.

`waydroid shell` did not reliably propagate command failures to the host exit
status. Read the actual output; exit0 alone is not a successful test.

After passing those checks, run:

```sh
pkexec /absolute/path/experiments/waydroid/accept-kernel.sh
```

This saves the recovery transaction, verifies recovery assets, permits the
normal kernel confirmation checks, disables the test timer, and enables the
container daemon. It removes only the update-pause marker this experiment
created. The local kernel remains pinned by APK's world constraint. Keep both
local APKs cached and the build's public signing key available for maintenance;
compare an existing key before installing it, never overwrite a different one.

The accepted kernel is local: upstream updates do not maintain this experiment.
Do not remove its pin or install a replacement kernel without planning a new
recovery test. Later boot-slot writes can invalidate the saved rollback.

## Return to the original kernel

Save your work. These commands run on the tablet after accepting the candidate:

```sh
pkexec /usr/local/sbin/dc1-waydroid-rollback --check
pkexec /usr/local/sbin/dc1-waydroid-rollback
```

The second command stops Android and reboots. It checks the running build,
original boot-image bytes and original package hashes, selects the retained
proven slot, restores its modules, and lets the confirmation service restore
its matching packages after boot. It refuses stale or inconsistent recovery
records. Android userdata is retained. **This manual recovery was exercised
end-to-end on the trial tablet**, followed by reinstalling and confirming the
Waydroid kernel.

Do not delete `/var/lib/dc1/waydroid-test` or `/var/lib/dc1/local-kernel` while
relying on this recovery path. After fallback, updates are paused deliberately;
review the restored state before removing `/var/lib/dc1/no-auto-update`.

## App installation and keyboard

The trial also installed [Aurora Store](https://f-droid.org/packages/com.aurora.store/)
4.8.4 and [F-Droid](https://f-droid.org/) 2.0.2 from F-Droid's official downloads.
Install downloaded Android APKs as the desktop user:

```sh
waydroid app install /path/to/application.apk
```

Aurora opened and reached sign-in; catalog downloads and app installation
through the stores were not independently verified. Aurora supports anonymous
access to Google Play apps. **Google Play services/GApps are not installed**;
apps requiring them may fail. Installing a store does not supply those services.
Android APKs are separate from Alpine's APK packages.

Typing began working after stopping and restarting the Android session following
the config permission fix. Restart with `waydroid session stop`, then
`waydroid show-full-ui`. To suppress the Android keyboard with hardware input,
run as root:

```sh
waydroid shell -- settings put secure show_ime_with_hard_keyboard 0
```

Use `1` to restore it. Waydroid exposes a persistent virtual hardware keyboard,
so Bluetooth disconnection may not automatically bring the screen keyboard back.

## Caveats and evidence limits

- Default ART and JIT-off alone crashed `system_server`; both interpreter flags
  were needed. [Waydroid issue2040](https://github.com/waydroid/waydroid/issues/2040)
  reports a related ARM64 Alpine crash signature. This is a workaround, not a
  root-cause fix.
- One initial kernel4 boot fell back before a Linux journal was recorded. Its
  cause remains unknown; subsequent boots succeeded.
- GPU rendering, Android DNS/HTTPS, host networking, Tailscale health and physical
  keyboard typing passed. Touch devices were detected, but a separate physical
  touch/gesture confirmation was not recorded.
- Audio, camera, suspend, DRM, banking apps, Play Integrity and long-term use
  were not validated. Interpreter performance varies by app.
- Android images are pinned local files; automatic image updates are not set up.
- The published helper refactoring has syntax/config checks, not another full
  hardware trial. Recovery evidence describes the equivalent commands exercised
  during the original installation, not a universal guarantee.

The underlying kernel retains GPL-2.0-only licensing. Upstream packaging and
installer code retain Denys Vitali's MIT notice in
[`LICENSE.upstream`](../experiments/waydroid/LICENSE.upstream). Local scripts and
documentation follow this repository's MIT license. No signing keys, boot dumps,
Android images, app binaries or personal configuration are published.
