#!/bin/bash
# UFW audit check with logging and session IDs

if [[ $EUID -ne 0 ]]; then
  echo "This script needs root - run it with sudo." >&2
  exit 1
fi

LOGFILE="/var/log/ufw-check.log"

# Generate session ID (timestamp + random hex)
SESSION_ID="$(date +%Y%m%d%H%M%S)-$RANDOM"

echo "=== UFW Audit Check ==="
echo "Session ID: $SESSION_ID"
echo "Timestamp : $(date '+%Y-%m-%d %H:%M:%S')"

# Collect states
svc_enabled=$(systemctl is-enabled ufw 2>/dev/null)
svc_state=$(systemctl is-active ufw 2>/dev/null)
fw_state=$(ufw status | grep -i "Status:")

echo "Service enabled: $svc_enabled"
echo "Service state  : $svc_state"
echo "Firewall state : $fw_state"

# Append to logfile
{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session $SESSION_ID"
  echo "  Service enabled: $svc_enabled"
  echo "  Service state  : $svc_state"
  echo "  Firewall state : $fw_state"
  echo "----------------------------------------"
} >> "$LOGFILE"
