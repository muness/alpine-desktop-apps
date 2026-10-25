#!/bin/sh
# Run only after the owner has tested the desktop, Android and input.
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run as root' >&2; exit 1; }
test "$(uname -r)" = 7.2.0-rc5-waydroid4
base=/var/lib/dc1/waydroid-test
test -f "$base/armed"
test "$(waydroid shell getprop sys.boot_completed | tr -d '\r\n')" = 1
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
install -m755 "$here/dc1-waydroid-rollback" /usr/local/sbin/dc1-waydroid-rollback
cp /var/lib/dc1/local-kernel/pending.json "$base/accepted-state.json"
/usr/local/sbin/dc1-waydroid-rollback --check
touch "$base/accept"
systemctl reset-failed dc1-local-kernel-confirm.service
systemctl start dc1-local-kernel-confirm.service
test ! -e /var/lib/dc1/local-kernel/pending.json
systemctl disable --now dc1-waydroid-recovery.timer
rm -f "$base/armed" "$base/accept" /etc/systemd/system/dc1-local-kernel-confirm.service.d/waydroid-test.conf
systemctl daemon-reload
systemctl enable waydroid-container.service
if [ -e "$base/created-no-auto-update" ]; then
 rm -f /var/lib/dc1/no-auto-update "$base/created-no-auto-update"
fi
/usr/local/sbin/dc1-waydroid-rollback --check
