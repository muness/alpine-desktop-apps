# Alpine desktop app experiment

Recipes and launchers from one attempt to run the **1Password desktop app**,
**ChatGPT desktop app with Codex**, and **BrowserOS neo** on a
Daylight DC-1 running Nura edge.
They use official ARM64 binaries inside a Debian/glibc filesystem, launched
with bubblewrap. The host stays on musl.

The APK was installed, removed and reinstalled on that tablet. All three
packaged apps opened; the owner confirmed 1Password and ChatGPT worked and
Neo loaded a web page. Completed sign-in, browser integration and long-term
use were not independently verified. No compatibility is claimed for other
machines, distributions or desktop sessions. See [what was tested](docs/testing.md).

There is no hosted APK repository or binary release here. Build locally if
you want to try it. Vendor binaries, runtime archives and signing keys are
not committed.

## Build

The current scripts expect a native **aarch64 Linux** build host with Podman,
Bash, curl, zstd and sha256sum. Rootless Podman worked on the build host used
for the original trial. Expect several GB of downloads, images and output;
the current runtime is about 3.4 GB unpacked and the APK is about 1.3 GB.

```sh
git clone https://github.com/muness/alpine-desktop-apps.git
cd alpine-desktop-apps
./scripts/build-runtime.sh
./scripts/build-apk.sh
```

The first script verifies the pinned vendor downloads, builds a Debian
runtime without reusing build layers and exports it to `out/runtime.tar.zst`.
Debian packages are fetched
from the configured repositories at build time, so repeat builds are not
claimed to be byte-identical. The second script builds a single APK in an
Alpine container and verifies its signature.

Output:

- `out/apk/`: the APK, containing the runtime and all three apps.
- `out/keys/packager.rsa.pub`: the public signing key for your build.
- `out/private/packager.rsa`: your private signing key. Keep it private;
  subsequent builds reuse it. The whole `out/` directory is ignored by Git.

`OUTPUT_DIR=/absolute/path` selects another output directory for either
script. Keep it outside tracked source files.

## Try the APK

The current build produces **one APK containing all three apps**. It has been
installed, removed and reinstalled on the trial DC-1. Review the recipe before
trusting a local build.

Copy the APK and its public signing key from the build host to your target.
Replace `USER@TARGET` with your SSH login:

```sh
ssh USER@TARGET 'mkdir -p ~/alpine-desktop-apps-install'
scp out/apk/glibc-desktop-apps-experimental-20261025-r1.apk \
    out/keys/packager.rsa.pub USER@TARGET:alpine-desktop-apps-install/
```

On the target, become root and change to that copied directory. Verify the
package, trust your build's public key, then install:

```sh
apk --repositories-file /dev/null --keys-dir . verify \
    ./glibc-desktop-apps-experimental-20261025-r1.apk
install -m644 packager.rsa.pub /etc/apk/keys/packager.rsa.pub
apk add ./glibc-desktop-apps-experimental-20261025-r1.apk
```

If `/etc/apk/keys/packager.rsa.pub` already exists, compare it with your public
key before installing; keep the existing file if it matches and do not overwrite
a different key. Copy only the public key to the target. The private key stays
on the build host.

This installs launchers named **1Password**, **ChatGPT**, and **BrowserOS neo**.
Leave the root shell and start them from the app grid or a terminal in your
Wayland desktop session:

```sh
1password
chatgpt
browseros-neo
# Alias for the same ChatGPT app, which includes Codex:
codex-desktop
```

The launcher currently assumes a Wayland session and supplies GNOME desktop
settings. It shares the user's home directory and session services with the
apps. It is a compatibility environment, **not a privacy boundary**.
Runtime executables have their setuid/setgid bits removed. Chromium/Electron's
setuid sandbox helper is skipped; the user-namespace sandbox stays
enabled. The launcher does not pass `--no-sandbox`.

The package does not change your default browser. If login callbacks do not
return to the app, register its URL handlers as your desktop user:

```sh
xdg-mime default chatgpt.desktop x-scheme-handler/codex
xdg-mime default com.onepassword.OnePassword.desktop x-scheme-handler/onepassword
xdg-mime default com.onepassword.OnePassword.desktop x-scheme-handler/onepassword8
```

### Replacing the earlier manual trial

Skip this section on a fresh installation. The earlier trial used launchers
in `/usr/local/bin` and a runtime at `/opt/dc1-desktop-runtime`. Those launchers
can hide the package's `/usr/bin` commands, and its desktop entries use the
same names as the package entries.

Close the apps before installing the APK. If you used that manual setup, move
its launchers and desktop entries aside as root:

```sh
backup=/var/lib/alpine-desktop-apps/manual-backup
mkdir -p "$backup/bin" "$backup/applications"
for name in 1password chatgpt codex-desktop; do
    [ ! -e "/usr/local/bin/$name" ] || mv "/usr/local/bin/$name" "$backup/bin/"
done
for name in com.onepassword.OnePassword.desktop chatgpt.desktop; do
    [ ! -e "/usr/share/applications/$name" ] || \
        mv "/usr/share/applications/$name" "$backup/applications/"
done
```

Then install the APK as above. Keep the old `/opt/dc1-desktop-runtime` until
you have checked all three apps. Existing app data in your home directory is
reused. The package itself does not perform this migration.

Check as your desktop user:

```sh
for app in 1password chatgpt browseros-neo; do command -v "$app"; done
apk info --who-owns /usr/bin/1password /usr/bin/chatgpt /usr/bin/browseros-neo
```

Each command should resolve to `/usr/bin`, and APK should report ownership by
`glibc-desktop-apps-experimental`. If it still resolves to `/usr/local/bin`,
check for a leftover launcher and clear your shell's command cache.

## Updates and removal

The initial pins are 1Password **8.12.42**, ChatGPT **26.1016.61520**, and
BrowserOS neo **0.51.2.3** (vendor Debian package version **155.0.8314.26**).
To update, review and change the vendor URLs/checksums, rebuild the runtime,
bump the APK version or release, close the apps, then build and install the new APK with
`apk add`. For Debian-library updates, rebuild the runtime and bump the APK
release too. `apk upgrade` cannot discover new builds unless you separately
publish and configure an APK repository.
The runtime is read-only, so vendor self-updaters cannot replace its files.
Use rebuilt packages for app updates.

As root:

```sh
apk del glibc-desktop-apps-experimental
```

This removes package-owned files, not app data in your home directory or a
previous manual install. Removal and reinstall were tested before launching
the packaged apps. An upgrade between different APK releases remains untested.
Remove your build's public key separately if you will no longer use it.

To return to the earlier manual trial, close the packaged apps, remove the APK,
then restore the saved files as root:

```sh
mv /var/lib/alpine-desktop-apps/manual-backup/bin/* /usr/local/bin/
mv /var/lib/alpine-desktop-apps/manual-backup/applications/* /usr/share/applications/
update-desktop-database /usr/share/applications
```

This rollback requires retaining the old `/opt/dc1-desktop-runtime`.

Browser-extension/desktop integration, biometric unlock, app updates and
long-term use remain untested. Firefox with the official 1Password extension
was used separately; Google login worked there. This repository does not
install Firefox or fix the Chromium cookie error encountered in the trial.

## Source and licenses

1Password comes from `downloads.1password.com`; ChatGPT comes from OpenAI's
`persistent.oaistatic.com` Debian feed. BrowserOS neo comes from the official
[browserclaw release](https://github.com/browseros-ai/BrowserOS/releases/tag/browserclaw/v0.51.2.3).
The build checks all three SHA-256 hashes; the Neo hash also matches the
GitHub release asset digest.
See [the build script](scripts/build-runtime.sh) for exact URLs and pins.

The scripts and documentation here are MIT-licensed. The vendor apps
and Debian components retain their own licenses, including the notices in
the generated filesystem. This repository does not publish their binaries.
