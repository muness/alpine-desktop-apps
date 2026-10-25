# Experimental Waydroid on the Daylight DC-1

Run Android 13 on a Daylight DC-1 with a custom kernel and native Alpine
Waydroid packages. On our DC-1 running Nura edge, GPU rendering, web browsing
and Brydge keyboard input worked. GNOME and Tailscale kept working too.

**Android needs interpreter mode to avoid a system-server crash.** Expect slow
startup and apps. We tested automatic fallback and manual recovery to the
original kernel.

Build locally using the scripts in this directory. This recipe is DC-1-specific
and does not use the glibc runtime. Follow the recovery steps before rebooting.

## Versions

| Component | Tested version |
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
pmbootstrap, Python, Git, Go and LLVM 20 inside its build environment. The
upstream build script uses sudo for its chroots; keep those calls intact.

From the repository root:

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

We built the tested kernel in an Alpine container using the original device
trees (DTBs). The wrapper here uses upstream's pmbootstrap recipe, which also
builds DTBs. Checkout preparation and all 11 config tests pass; we have not
repeated the full build and device installation through this wrapper.
Use a new recovery transaction for each build, with its own checksums.

## Prepare recovery before installing

Start with a charged DC-1 running its original Linux kernel and working SSH.
Back up important data and stay with the tablet for the first boot.

Copy the prepared source checkout, both APKs, public keys, and this repository's
`experiments/waydroid` directory to the tablet. Build the boot-image helper on
aarch64 Linux with `(cd boot/mkboot && go build -o mkboot .)` inside the prepared
checkout. Keep its executable in that checkout.

The guarded installer requires the installed `dc1-boot-sync` helper to match its
pinned source exactly. It also checks boot-image provenance, installed kernel
parity, APK signatures and availability of the original packages. If a check
fails, resolve the mismatch before proceeding.

Record `uname -r` and `dc1-slotctl status`. Run the supplied recovery preparation
script as root (use absolute paths with graphical polkit):

```sh
pkexec /absolute/path/experiments/waydroid/arm-recovery.sh
```

It backs up the original module tree, pauses automatic updates, installs a
confirmation gate, and enables a ten-minute timer for the candidate kernel.
It refuses a pending or previously accepted experiment. Keep the original
Linux slot intact. Never write preloader, lk, dtbo or vendor_boot partitions.

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
review.

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
Check that it uses the preinstalled images. In `/var/lib/waydroid/waydroid.cfg`, add
these entries to its existing `[properties]` section:

```ini
dalvik.vm.extra-opts = -Xint
dalvik.vm.usejit = false
```

Keep the config readable by the desktop user (`chmod 644`). Mode `600`
prevented the Binder helper from reading it. Run `waydroid upgrade -o` as root to
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

Startup took about two minutes. To start Android only when needed, put this in
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
`waydroid shell -- dumpsys SurfaceFlinger` for the GPU renderer. Our tablet
reported Mali-G57 MC2 / Panfrost / Mesa 26.0.8. Test touch and typing in an
Android text field. Check host browsing and any VPN as well.

`waydroid shell` did not reliably propagate command failures to the host exit
status. Read the output; exit code `0` alone does not establish success.

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

You maintain this custom kernel; upstream updates do not cover it.
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
records and keeps Android userdata. We tested this rollback, then reinstalled
and confirmed the Waydroid kernel.

Do not delete `/var/lib/dc1/waydroid-test` or `/var/lib/dc1/local-kernel` while
relying on this recovery path. After fallback, updates are paused deliberately;
review the restored state before removing `/var/lib/dc1/no-auto-update`.

## App installation and keyboard

We also installed [Aurora Store](https://f-droid.org/packages/com.aurora.store/)
4.8.4 and [F-Droid](https://f-droid.org/) 2.0.2 from F-Droid's official downloads.
Install downloaded Android APKs as the desktop user:

```sh
waydroid app install /path/to/application.apk
```

Aurora reached sign-in. We have not tested downloads through either store.
Aurora supports anonymous access to Google Play apps, but does not install
Google Play services. Apps that require those services need a separate GApps
setup. These Android APKs are unrelated to Alpine packages.

After fixing the config permissions, we had to restart Android before the
Brydge could type. Restart with `waydroid session stop`, then
`waydroid show-full-ui`. To suppress the Android keyboard with hardware input,
run as root:

```sh
waydroid shell -- settings put secure show_ime_with_hard_keyboard 0
```

Use `1` to restore it. Waydroid exposes a persistent virtual hardware keyboard,
so Bluetooth disconnection may not automatically bring the screen keyboard back.

## Remaining issues

- Default ART and JIT-off alone crashed `system_server`. Keep both interpreter
  flags. [Waydroid issue #2040](https://github.com/waydroid/waydroid/issues/2040)
  reports a related ARM64 Alpine crash; the cause is unresolved.
- The first kernel4 boot fell back without recording a Linux journal.
  Subsequent boots succeeded; we do not know why the first failed.
- Physical touch/gestures, audio, camera, suspend, DRM, banking apps,
  Play Integrity and long-term stability remain untested.
- Android image updates are manual.

## Files

| File | Purpose |
| --- | --- |
| `prepare-kernel.sh` | Checks out pinned upstream sources and applies the local recipe changes; does not flash hardware. |
| `kernel.patch`, `waydroid.config` | Kernel package changes and required configuration. |
| `installer.patch` | Local adjustments to upstream's guarded kernel installer. |
| `images.json`, `fetch-images.py` | Official Android image pins and download verification. |
| `arm-recovery.sh` | Prepares original modules, the confirmation gate and timed fallback before installation. |
| `accept-kernel.sh` | Confirms a tested candidate and disables its test timer. |
| `dc1-waydroid-rollback` | Checks retained recovery assets and restores the original kernel after acceptance. |
| `LICENSE.upstream` | License notice for upstream packaging and installer code. |

## Licenses

The underlying kernel retains GPL-2.0-only licensing. Upstream packaging and
installer code retain Denys Vitali's MIT notice in
[`LICENSE.upstream`](LICENSE.upstream). Local scripts and
documentation follow this repository's MIT license.
