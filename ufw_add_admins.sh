#!/bin/bash
# Open UFW for SSH (port 22/tcp) from a list of trusted admin IPs, each
# tagged with a comment so ufw_check.sh's output shows why that address is
# allowed - see the real example in appendix-jump-box-hardening.md.
#
# Doesn't touch any existing wide-open "Anywhere" rule - see that appendix
# for removing it safely (add these scoped rules, confirm they work, then
# delete the wide-open one, in that order).
#
# Reads "user,ip" pairs from ufw-admins.txt (one per line, blank lines and
# lines starting with # ignored).

set -e

FILE="${1:-ufw-admins.txt}"

if [[ ! -f "$FILE" ]]; then
  echo "Missing $FILE - create it with one 'user,ip' pair per line" >&2
  exit 1
fi

while IFS=',' read -r user ip; do
  user="$(echo "$user" | xargs)"
  [[ -z "$user" || "$user" == \#* ]] && continue
  ip="$(echo "$ip" | xargs)"
  if [[ -z "$ip" ]]; then
    echo "Missing IP for $user in $FILE - each line needs 'user,ip'" >&2
    exit 1
  fi

  sudo ufw allow from "$ip" to any port 22 proto tcp comment "${user}-admin-ssh"
done < "$FILE"

sudo ufw reload

# Show the resulting ruleset, sorted numerically by source IP. Same
# approach as ufw_add_switches.sh / ufw_check.sh: ufw right-pads
# single-digit rule numbers with a space ("[ 4]", two tokens) but not
# double-digit ones ("[10]", one token), so a fixed field number shifts
# once rule numbers reach 10 - finding whichever field looks like an IPv4
# address sidesteps that regardless of rule-number width.
ufw_status="$(sudo ufw status numbered)"
echo "$ufw_status" | head -4
echo "$ufw_status" | tail -n +5 | awk '{
  key = ""
  for (i = 1; i <= NF; i++) {
    if ($i ~ /^[0-9]{1,3}(\.[0-9]{1,3}){3}$/) { key = $i; break }
  }
  print key "\t" $0
}' | sort -k1,1 -V | cut -f2-
