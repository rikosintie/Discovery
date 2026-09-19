#!/bin/bash
# Check UFW service and firewall status together

if [[ $EUID -ne 0 ]]; then
  echo "This script needs root - run it with sudo." >&2
  exit 1
fi

echo "===UFW Service State (systemd)==="
systemctl is-enabled ufw
systemctl is-active ufw

echo
echo "===UFW Firewall Rule State==="
ufw status verbose

echo "Combined Summary"
svc_state=$(systemctl is-active ufw)
fw_state=$(ufw status | grep -i "Status:")

echo "===Summary==="
echo "Service: $svc_state"
echo "Firewall: $fw_state"
