#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo "Run as root" >&2; exit 1; }
test ! -e /var/lib/dc1/local-kernel/pending.json
test ! -e /var/lib/dc1/waydroid-test/accepted-state.json
case "$(uname -r)" in *waydroid*) echo "Start from a proven original kernel" >&2; exit 1;; esac
base=/var/lib/dc1/waydroid-test
mkdir -p "$base/rollback" /etc/systemd/system/dc1-local-kernel-confirm.service.d
test ! -e "$base/armed"
test -d "/lib/modules/$(uname -r)"
tar -cf "$base/rollback/modules.tar" -C / "lib/modules/$(uname -r)"
if [ ! -e /var/lib/dc1/no-auto-update ]; then
 touch /var/lib/dc1/no-auto-update "$base/created-no-auto-update"
fi
cat > "$base/confirm-gate.py" <<'PY'
from pathlib import Path
import json, os, sys
pending=Path('/var/lib/dc1/local-kernel/pending.json')
if pending.exists():
 state=json.loads(pending.read_text())
 if Path('/proc/version').read_text().strip()==state['new_banner'] and not Path('/var/lib/dc1/waydroid-test/accept').exists():
  sys.exit('Waydroid test remains unconfirmed; recovery timer is armed')
os.execv('/usr/bin/python3',['python3','/var/lib/dc1/local-kernel/confirm.py','confirm'])
PY
cat > /etc/systemd/system/dc1-local-kernel-confirm.service.d/waydroid-test.conf <<'UNIT'
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /var/lib/dc1/waydroid-test/confirm-gate.py
UNIT
cat > "$base/recover.sh" <<'RECOVER'
#!/bin/sh
set -eu
[ -f /var/lib/dc1/waydroid-test/armed ] || exit 0
[ "$(uname -r)" = 7.2.0-rc5-waydroid4 ] || exit 0
systemctl stop waydroid-container.service || true
sync
systemctl reboot
RECOVER
chmod 700 "$base/recover.sh"
cat > /etc/systemd/system/dc1-waydroid-recovery.service <<'UNIT'
[Unit]
Description=Reboot unconfirmed Waydroid test into proven fallback
[Service]
Type=oneshot
ExecStart=/var/lib/dc1/waydroid-test/recover.sh
UNIT
cat > /etc/systemd/system/dc1-waydroid-recovery.timer <<'UNIT'
[Unit]
Description=Ten minute recovery deadline for Waydroid kernel test
[Timer]
OnBootSec=10min
Unit=dc1-waydroid-recovery.service
[Install]
WantedBy=timers.target
UNIT
touch "$base/armed"
rm -f "$base/accept"
systemctl daemon-reload
systemctl enable dc1-waydroid-recovery.timer
systemd-analyze verify /etc/systemd/system/dc1-waydroid-recovery.service /etc/systemd/system/dc1-waydroid-recovery.timer
printf 'Old modules backed up; confirmation gate and recovery timer installed.\n'
