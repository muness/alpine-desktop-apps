# Obsidian ARM64 add-on

This recipe packages the [official Obsidian 1.14.5 ARM64 tarball](https://github.com/obsidianmd/obsidian-releases/releases/tag/v1.14.5)
for the glibc runtime already used by this project. It produces a separate
`obsidian-glibc-experimental` APK. Updating or removing Obsidian does not require
rebuilding the base runtime.

Only the Daylight DC-1 / Nura edge / GNOME Mobile setup recorded below was
tested. Other devices and desktops are unverified.

## Build

From the repository root:

```sh
./scripts/build-obsidian-apk.sh
```

Output: `out/apk/obsidian-glibc-experimental-1.14.5-r0.apk`, roughly 130 MB
compressed and 348 MB unpacked. The build uses the existing local signing key,
or creates one using the same helper as the other recipes.

The vendor archive's SHA-256 was checked against the GitHub release asset digest:

```text
ba1d2e7070acffb39a795e81c48c3a2119c44be526337dd8ff58963f3ab2052a
```

The APKBUILD pins SHA-512 checksums for the archive and launchers. Its build only
unpacks vendor binaries; the helper skips installing the runtime dependency into
the disposable build container. The generated APK retains that dependency,
and APK enforces it at installation.

## Install

The target needs `glibc-desktop-apps-experimental` version `20261025-r1` or newer.
On a fresh target, first build and install the [base runtime APK](../README.md#build).
The existing manual `/opt/dc1-desktop-runtime` setup does not satisfy this dependency.

Copy the Obsidian APK and your public signing key to the target. Follow the
[signing-key instructions](../README.md#try-the-apk), then, as root in the directory
containing those files:

```sh
apk --repositories-file /dev/null --keys-dir . verify \
    ./obsidian-glibc-experimental-1.14.5-r0.apk
apk add ./obsidian-glibc-experimental-1.14.5-r0.apk
```

Start **Obsidian** from the app grid, or run `obsidian` in your Wayland desktop
session as your regular user. Open or create a vault in your home directory.
The runtime shares your home with the app, so notes remain ordinary files there.

To register Obsidian links, as your desktop user:

```sh
xdg-mime default obsidian.desktop x-scheme-handler/obsidian
```

## Package layout and updates

The add-on owns `/usr/bin/obsidian`, its desktop entry and
`/usr/lib/desktop-apps-runtime/opt/obsidian`. The base runtime's read-only root
mount includes those files. The launcher uses its existing `shell` entry point
to run Obsidian with native Wayland and the setuid sandbox helper disabled.
It does not pass `--no-sandbox`.

To update the installer, review a new official ARM64 tarball, update the URL,
version and checksums, then rebuild and install the add-on APK. The base runtime
can remain installed. Obsidian's own in-profile app updates were not tested.

Close Obsidian before removing or upgrading it. As root:

```sh
apk del obsidian-glibc-experimental
```

Removal deletes the packaged app, launcher and desktop entry. It leaves the
base runtime, your vaults and your Obsidian settings in place. Upgrading the
base runtime while this add-on is installed remains untested.

## DC-1 checks, 2026-10-25

- Official vendor download digest matched; local APK build and signature verification passed.
- The signed APK installed, was removed, and was reinstalled on the tablet.
- APK reported ownership of the Obsidian executable and launcher.
- Removal left the base launcher checksum unchanged and kept the packaged 1Password, ChatGPT and Neo executables.
- Obsidian stayed running from the packaged runtime in the GNOME Wayland session; the owner confirmed the initial app check was successful.
- A dedicated `~/Documents/Obsidian APK Test` vault was prepared; no existing Obsidian configuration was overwritten.
- Obsidian created a note, appended to it, and persisted both changes. The final append was sent through `/usr/bin/obsidian` using the official URI protocol and checked on disk.

The initial renderer snapshot showed seccomp mode 0 and two PID namespace
levels. The distributed app enables Node integration in its renderer; do not
assume the renderer sandbox observations for the other apps apply to Obsidian.
The runtime is a compatibility environment, not a privacy boundary.

Logs reported native EGL initialization failures because the existing runtime
lacks `libEGL.so.1`. The app continued and opened its workspace, but hardware
acceleration is unverified. Heavy graphs, community plugins, Sync, account
sign-in, the optional CLI setting and long-term use were not tested.
