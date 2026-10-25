# What was tested

## Manual trial, 2026-10-25

- Device: Daylight DC-1, ARM64, GNOME Mobile on Nura edge.
- Kernel/modules: `linux-postmarketos-mediatek-mt6789-7.2_rc5_git20260819-r67`.
- Device package: `device-daylight-jagar-1-r116`.
- Compositor: `mutter-mobile-999948.0-r6`.
- 1Password desktop: `8.12.42`, official ARM64 tarball.
- ChatGPT/Codex desktop: `26.1016.61520`, official ARM64 Debian package.

A Debian trixie filesystem supplied glibc and the app dependencies. The host's
C library and kernel were unchanged. The app processes ran as the desktop
user, with Wayland, audio, the home directory and session D-Bus available.
The owner confirmed both application windows displayed and allowed starting
sign-in. Completed authentication, vault operations and Codex tasks were not
independently verified.

Both apps stayed running. For each app, three renderer processes showed
seccomp mode 2 and four PID namespace levels. Those observations confirm
that the tested launch did not turn off renderer seccomp; they are not a
security audit or proof of complete sandbox isolation. Home and desktop
services are deliberately shared.

Firefox 154 with the official 1Password extension 8.12.41.1 was installed
separately. The owner confirmed Google login worked in Firefox. Chromium
had reported cookies disabled; that failure was not diagnosed or repaired.

## Differences in the recipe

The manual trial extracted the runtime directly to `/opt/dc1-desktop-runtime`
and used `/usr/local/bin` launchers. This repository packages it under
`/usr/lib/desktop-apps-runtime` with `/usr/bin` launchers. The launcher also creates
a temporary `/home` mount before binding the user's home. The package strips
setuid/setgid bits from runtime executables; those helpers are not used by
the launcher.

The recipe started from the manual setup. The later APK test below verifies
the packaged paths on the same tablet; it does not establish compatibility
elsewhere.

## Local build checks, 2026-10-25

On a native aarch64 Linux host with rootless Podman:

- Both pinned vendor download checksums passed, including a fresh download
  from the versioned 1Password URL.
- The runtime built from the repository Dockerfile.
- Alpine 3.22 / abuild 3.15.0 produced the aarch64 APK, roughly 1.1 GB
  compressed and 2.7 GB unpacked. Package postchecks passed.
- The generated APK signature verified with the locally generated public key.
- Shell syntax, ShellCheck, desktop-entry validation and local Markdown links
  passed. GitHub source checks also passed.

These initial build checks preceded the APK installation test below.

## Still open

- Upgrade between different APK releases on the tablet.
- Completed sign-in and normal app use over time.
- 1Password browser integration and biometric/system authentication.
- A second user ID, another desktop, X11, or another device/distribution.
- Future vendor releases and a maintained update feed.

## BrowserOS neo recipe, 2026-10-25

The official ARM64 `.deb` for Neo **0.51.2.3** reports Debian package version
**155.0.8314.26**. Its SHA-256 matched both the existing host recipe and the
GitHub release asset digest. No Neo package was found in the DC-1's configured
APK repositories.

The Debian runtime installed Neo without additional dependencies. The updated
runtime and `20261025-r1` APK built locally; package postchecks and signature
verification passed. The APK is about 1.3 GB compressed and 3.4 GB unpacked.
ShellCheck, shell syntax and desktop-entry validation passed for the launchers.

## APK installation and application test, 2026-10-25

The `20261025-r1` APK contains all three apps. It was transferred to the same
DC-1, checked against the build-host SHA-256, verified with the build's public
key, and installed with `apk add`. The previous manual launchers and desktop
entries were moved to `/var/lib/alpine-desktop-apps/manual-backup`; the old
runtime was retained for rollback. App data in the user's home was retained.

Package lifecycle checks passed:

- APK reported ownership of all three `/usr/bin` launchers and Neo's desktop entry.
- `apk del` removed the launchers, Neo's desktop entry and the packaged runtime.
- The old manual runtime and the user's configuration directory remained.
- Reinstalling the same signed APK succeeded.

After reinstall, each app was launched through its `/usr/bin` launcher in the
GNOME Wayland session. All three user services stayed active, and their mount
information included `/usr/lib/desktop-apps-runtime`, confirming use of the
packaged runtime. The owner confirmed all three worked, including Neo opening
its window and loading the requested web page.

At one process snapshot, 1Password had one renderer, ChatGPT had three, and
Neo had seven. Each identified renderer showed seccomp mode 2 and four PID
namespace levels. Renderer counts change during use; these checks are not a
security audit. The launcher shares the user's home and desktop services.

Completed authentication, vault operations, Codex tasks, Neo agent pairing,
extensions and updates remain unverified. The test did not upgrade between
different APK releases or exercise the documented return to the old manual
installation. No other device or desktop was tested.

### USB transfer finding

Wi-Fi became too slow for the package transfer. USB supplied power but Linux's
UDC stayed at `not attached`. A timed, reversible PHY session override restored
CDC-ECM enumeration and authenticated SSH over USB, which carried the APK.
This was a diagnostic register test, not a flashed kernel or a recipe dependency.
The temporary override was restored after testing.

Evidence: [DC-1 issue #13](https://github.com/denysvitali/dc-1-pmos/issues/13).
The [draft kernel fix](https://github.com/denysvitali/dc-1-linux-kernel/pull/5)
compiled, but a patched-kernel boot and cable/role-transition tests remain pending.

## Native Tailscale applet

The separate Tailscale QS APK was built, installed, removed and reinstalled.
After browser sign-in, the daemon was online with no health warnings. The
installed applet's control model successfully disconnected and reconnected
the VPN as the desktop user. See [setup and exact checks](tailscale.md).

After the desktop-apps trial, the owner requested BrowserOS neo as the default
browser and removal of Firefox. Those changes were applied on the tablet.
The earlier Firefox observations above describe the original trial.

Tailscale follow-up: the owner later reported severe browsing slowdown and an
unresponsive toggle. A reboot restored normal traffic. A subsequent staged
retry with Tailscale DNS disabled and the applet enabled passed page loads,
repeated downloads, large-packet LAN pings and a VPN peer ping; the owner
reported it seemed great. The cause of the earlier failure remains unproven.
A further DNS-on retest also passed public lookups, repeated downloads,
MagicDNS resolution and all 15 large-packet pings; the owner confirmed normal
browsing. Tailscale DNS is now enabled. The [instructions](tailscale.md) record
both tests and retain the earlier failure as unresolved.
