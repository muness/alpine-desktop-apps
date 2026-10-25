# Experimental Waydroid on the Daylight DC-1

A kernel recipe and Android setup tested together on one DC-1 running Nura
edge. The kernel enables the support Waydroid needs; it is not intended for
other devices or proposed as a replacement for the default DC-1 kernel.

**Start with the [setup, testing and recovery guide](../../docs/waydroid.md).**
It covers build prerequisites, installing matching kernel/modules packages,
preparing fallback before reboot, Android setup, app stores and rollback.
Do not run the recovery helpers out of sequence.

## Status

Android 13 booted with GPU rendering, DNS and HTTPS access. Brydge keyboard
input worked after restarting the Android session. GNOME and Tailscale remained
usable. Timed fallback and manual restoration of the original kernel were
exercised on the trial tablet.

Android currently requires **interpreter mode** to avoid a system-server crash,
so startup and apps can be slow. Audio, camera, suspend and long-term stability
are untested. GApps is not installed; Aurora Store and F-Droid are documented
alternatives for installing apps.

The published preparation wrapper and configuration checks pass, but a fresh
full build and hardware installation using this wrapper have not been repeated.
See the guide for the exact tested versions and remaining limitations.

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

No kernel binaries, Android images, boot dumps or signing keys are published
here. No upstream PR has been opened for this experiment.
