# Tailscale with a GNOME Quick Settings applet

Tailscale itself is available from Alpine. This repository packages the
community-maintained [Tailscale QS](https://github.com/tailscale-qs/tailscale-gnome-qs)
GNOME extension separately. It adds a connection toggle, peer list and exit-node
controls to Quick Settings. It does not provide an initial sign-in screen.

This package uses Alpine's native Tailscale daemon and GJS. It does not use the
Debian/glibc runtime or require the large desktop-apps APK. The extension's
metadata lists GNOME Shell 48–51; only GNOME Mobile 48 on the trial DC-1 has
been tested here. It is not an official Tailscale GUI.

## Build and install

On the build host:

```sh
./scripts/build-tailscale-qs-apk.sh
```

This produces `out/apk/gnome-shell-extension-tailscale-qs-11-r0.apk` and uses the
same local signing key as the desktop-apps build. It verifies pinned upstream
ZIP and license checksums; it does not regenerate remote-source checksums.

Copy the APK and `out/keys/packager.rsa.pub` to the target. Follow the
[signing-key instructions](../README.md#try-the-apk) before installing the key.
From the directory containing the copied files, as root:

```sh
apk --repositories-file /dev/null --keys-dir . verify \
    ./gnome-shell-extension-tailscale-qs-11-r0.apk
apk add tailscale tailscale-systemd ./gnome-shell-extension-tailscale-qs-11-r0.apk
systemctl enable --now tailscaled.service
```

Tailscale **1.102.5-r0** and applet **11-r0** were used in the trial.
The service commands above are for the systemd-based trial device. Other init
systems were not tested. Tailscale and `tailscale-systemd` come from the target's
configured Alpine repositories; this project does not rebuild either package.

## Sign in, then enable the applet

Still as root, replace `YOUR_DESKTOP_USER` with the desktop login name:

```sh
tailscale up --accept-dns=false --operator=YOUR_DESKTOP_USER
```

`--accept-dns=false` keeps the network's DNS configuration. This is the
configuration that passed the follow-up test below; system-wide MagicDNS
resolution is not enabled by these instructions. Tailscale IP connectivity and
the applet's peer list still work.

Open the printed authentication link in your browser and complete sign-in and
device approval. Do not substitute the root account for your desktop username.
The operator setting lets that desktop user control Tailscale without a root
prompt. Initial sign-in was run with administrative permissions in the trial;
the unauthenticated user-level `tailscale login` attempt was denied.

Finish sign-in before enabling the applet. If it is already enabled, disable
it while completing initial authentication; this avoids changing the VPN state
while you are approving a browser link.

Log out of GNOME and back in so Shell discovers the newly installed extension.
Then, in a terminal as your desktop user:

```sh
gnome-extensions enable tailscale-gnome-qs@tailscale-qs.github.io
gnome-extensions info tailscale-gnome-qs@tailscale-qs.github.io
tailscale status
```

The extension should report `State: ACTIVE`. Open Quick Settings at the top
right. Tap the **main Tailscale tile** to connect/disconnect; tap the **arrow**
to open the peer and exit-node menu. The arrow is not the connection toggle. Signing in and choosing an exit node
are separate actions; no exit node is configured by these instructions.

For Tailscale CLI details, see the [official documentation](https://tailscale.com/kb/1080/cli).

## Nura extension-launcher workaround

On the trial system, `gnome-extensions` initially failed to connect to GNOME
Shell. Its D-Bus activation file launched `/usr/sbin/gjs`, which did not exist;
the installed GJS executable was `/usr/bin/gjs`.

Only if your system has that same mismatch, run this as your desktop user:

```sh
service=org.gnome.Shell.Extensions.service
mkdir -p "$HOME/.local/share/dbus-1/services"
sed 's|^Exec=/usr/sbin/gjs |Exec=/usr/bin/gjs |' \
    "/usr/share/dbus-1/services/$service" \
    > "$HOME/.local/share/dbus-1/services/$service"
gdbus call --session --dest org.freedesktop.DBus \
    --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.ReloadConfig
```

Preserve any existing user override before writing that file. This changes the
user's activation entry, not the distro-owned file. Remove the override once
the distro fixes its launcher. The workaround is not part of the applet APK.

## Disable or remove

As your desktop user:

```sh
gnome-extensions disable tailscale-gnome-qs@tailscale-qs.github.io
```

As root:

```sh
apk del gnome-shell-extension-tailscale-qs
```

Removing the applet leaves the Tailscale daemon and its login state in place.
To disconnect the VPN, use `tailscale down`; to remove the daemon too, stop its
service and remove `tailscale-systemd` and `tailscale` separately. These are
separate from deleting a device in your tailnet's admin console.

## DC-1 test, 2026-10-25

- The applet APK built locally, passed package checks and verified with the local signing key.
- Alpine's Tailscale and systemd service APKs verified with Alpine's trusted keys and installed.
- The applet APK installed, was removed with its extension directory gone, then reinstalled.
- After a fresh GNOME session, the owner saw the applet and Shell reported it `ACTIVE` from the package-owned system path.
- Initial sign-in completed in the browser; the daemon reached `Running`, online, with no health warnings.
- A GJS test imported the installed applet's actual `Tailscale` model as the desktop user. Its API disconnected and reconnected the VPN successfully.
- A Tailscale peer ping received a reply. No exit node, subnet routes or Tailscale SSH were configured for this test.
- The shared build helper was also rerun for the existing desktop-apps APK; that build and signature check passed.

The CLI/API control round trip was automated; a physical tap on the applet's
tile was not independently observed. Exit-node selection, account switching,
suspend/resume and long-term use remain untested.

### Follow-up: slowdown and retry

Later, the owner reported nearly unusable browsing and an unresponsive applet
toggle. SSH stalled too. Large LAN ping packets were lost while smaller ones
passed; Tailscale already reported disconnected, with no exit node or accepted
subnet routes. The daemon and applet were stopped, and a reboot restored normal
browsing and full-size packets. This does not establish Tailscale as the cause.

A staged retry then enabled Tailscale with `--accept-dns=false`, followed by the
applet. The daemon was online with no health warnings. Page loads took about
0.1 seconds; repeated 1 MB downloads ran at roughly 4–5 MB/s; all 12 large LAN
ping packets arrived, and a VPN peer ping succeeded. Asked about browsing and
the applet toggle, the owner reported “seems great.”

The daemon and applet were left enabled, with Tailscale DNS disabled. This is
a successful short retest, not proof that DNS caused the earlier failure or
that it cannot recur. The earlier temporary host packet-size adjustment was
removed; the tablet's Wi-Fi MTU remained 1500.
