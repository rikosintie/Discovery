#!/bin/bash
# Check UFW service and firewall status together. Plain, for an ad-hoc
# interactive check. With --log, also appends a timestamped, session-ID'd
# snapshot to /var/log/ufw-check.log - run it that way from cron for a
# running audit trail of whether the firewall stayed enabled and
# configured as expected.

if [[ $EUID -ne 0 ]]; then
  echo "This script needs root - run it with sudo." >&2
  exit 1
fi

LOGFILE="/var/log/ufw-check.log"
log_mode=false
[[ "$1" == "--log" ]] && log_mode=true

svc_enabled=$(systemctl is-enabled ufw 2>/dev/null)
svc_state=$(systemctl is-active ufw 2>/dev/null)
fw_state=$(ufw status | grep -i "Status:")

if $log_mode; then
  session_id="$(date +%Y%m%d%H%M%S)-$RANDOM"
  echo "=== UFW Audit Check ==="
  echo "Session ID: $session_id"
  echo "Timestamp : $(date '+%Y-%m-%d %H:%M:%S')"
else
  echo "===UFW Service State (systemd)==="
fi

echo "Service enabled: $svc_enabled"
echo "Service state  : $svc_state"
echo "Firewall state : $fw_state"

if $log_mode; then
  {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session $session_id"
    echo "  Service enabled: $svc_enabled"
    echo "  Service state  : $svc_state"
    echo "  Firewall state : $fw_state"
    echo "----------------------------------------"
  } >> "$LOGFILE"
fi
