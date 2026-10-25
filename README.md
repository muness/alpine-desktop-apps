# Alpine desktop app experiment

Recipes and launchers from one attempt to run the **1Password desktop app**,
**ChatGPT desktop app with Codex**, and **BrowserOS neo** on a
Daylight DC-1 running Nura edge.
They use official ARM64 binaries inside a Debian/glibc filesystem, launched
with bubblewrap. The host stays on musl.

The 1Password and ChatGPT windows opened on that tablet and allowed
starting sign-in. Neo has passed local build checks; its tablet launch test
is pending. This is not a claim that the setup works on other machines,
distributions or desktop sessions. The APK packaging is
an experiment too. See [what was tested](docs/testing.md).

There is no hosted APK repository or binary release here. Build locally if
you want to try it. Vendor binaries, runtime archives and signing keys are
not committed.

## Build

The current scripts expect a native **aarch64 Linux** build host with Podman,
Bash, curl, zstd and sha256sum. Rootless Podman worked on the build host used
for the original trial. Expect several GB of downloads, images and output;
the runtime alone is around 3 GB unpacked.

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

The package has not been installed on the tablet used for the original manual
trial yet. Review the recipe before trusting a local build. Copy the APK and
its public key to the target. As root on that target, using the correct paths:

```sh
install -m644 out/keys/packager.rsa.pub /etc/apk/keys/
apk add out/apk/glibc-desktop-apps-experimental-20261025-r1.apk
```

This installs launchers named **1Password**, **ChatGPT**, and **BrowserOS neo**.
They can also be started from a terminal:

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

The original manual trial used `/usr/local/bin` launchers and
`/opt/dc1-desktop-runtime`. This recipe uses `/usr/bin` and
`/usr/lib/desktop-apps-runtime`; it does not migrate or remove a previous manual
installation. An old `/usr/local/bin` launcher may take precedence.

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
previous manual install. Remove your build's public key separately if you
will no longer use it.

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
