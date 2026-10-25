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

The recipe records the manual setup rather than claiming a tested general
solution. Local build checks are recorded below as they are completed.

## Still open

- Install, upgrade and removal of this APK on the tablet.
- Completed sign-in and normal app use over time.
- 1Password browser integration and biometric/system authentication.
- A second user ID, another desktop, X11, or another device/distribution.
- Future vendor releases and a maintained update feed.
