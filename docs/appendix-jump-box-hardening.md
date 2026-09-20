# Restricting SSH on the Automation Host

Whether it's running the full [Automating Discovery](appendix-discovery-automation.md)
setup, the standalone [Daily Switch Backup](appendix-daily-switch-backup.md),
or both, the automation host is effectively a jump box — it holds
management access to every switch (and firewall) on the network, over SSH,
SNMP, or TFTP. That makes its own SSH access worth locking down, not
leaving open to the whole LAN.

## Why this matters here specifically

Both appendices above install `openssh-server` and get SSH working, but
neither one scopes *who* can reach it — `sudo ufw allow ssh` (used in both)
allows port 22 from `Anywhere`. The other two services are already scoped
tightly enough that this is the one gap left:

- SNMP on the firewall is restricted to this host's own IP (see
  [Polling a Firewall's ARP Table via SNMP](appendix-firewall-arp-snmp.md)).
- TFTP on this host is restricted to the switches' IPs, one rule per switch
  (see [Daily Switch Backup](appendix-daily-switch-backup.md)) — and
  nothing about that setup means a switch ever needs to reach this host
  over SSH, so there's no reason to fold SSH into that same allow-list.

SSH is the one service actually meant for a human to use interactively —
which also makes it the one worth aiming at a specific person's laptop or
a management subnet, not the whole LAN.

## Scope SSH to a management subnet or a short allow-list

Two equivalent patterns — pick whichever matches the site.

**A dedicated management subnet**, if one exists:

```bash
sudo ufw allow from 10.100.100.0/24 to any port 22 proto tcp
```

**A short list of trusted hosts**, if it doesn't — your own laptop, an
MSP's jump host, maybe a couple of coworkers. `ufw_add_admins.sh` adds one
tagged rule per person from a list, so `sudo ufw status verbose` shows
*why* each address is allowed instead of a bare IP to puzzle over later —
and [ufw_check.sh](appendix-daily-switch-backup.md#4-verify-and-monitor)
picks up the same comments in its own output.

There's no repo to clone this out of, so create it directly:

```bash
cd ~
touch ufw_add_admins.sh
nano ufw_add_admins.sh
```

Paste the following into nano, then `ctrl+o` to save, `ctrl+x` to close it:

```bash
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
```

```bash
chmod +x ufw_add_admins.sh
```

`ufw-admins.txt` — `user,ip` pairs, one per line:

```bash
cat > ufw-admins.txt << 'EOF'
mhubbard,10.100.126.110
msp-admin,10.100.126.50
EOF

./ufw_add_admins.sh ufw-admins.txt
```

```text
Status: active

     To                         Action      From
     --                         ------      ----
[ 2] 22/tcp                     ALLOW IN    10.100.126.50              # msp-admin-admin-ssh
[ 3] 22/tcp                     ALLOW IN    10.100.126.110             # mhubbard-admin-ssh
[ 1] 22/tcp                     ALLOW IN    Anywhere
```

To review the rules again later — including alongside TFTP's, if this host
also runs [Daily Switch Backup](appendix-daily-switch-backup.md)'s
`ufw_add_switches.sh` — use
[ufw_check.sh](appendix-daily-switch-backup.md#4-verify-and-monitor)
instead of `ufw status` directly; it prints the same sorted ruleset plus
the service/firewall summary. Real example from a host running both:

```bash
sudo ./ufw_check.sh
```

```text
===UFW Service State (systemd)===
Service enabled: enabled
Service state  : active
Firewall state : Status: active

Status: active

     To                         Action      From
     --                         ------      ----
[ 3] 22/tcp                     ALLOW IN    192.168.10.143             # G5-wireless-admin-ssh
[ 4] 22/tcp                     ALLOW IN    192.168.10.223             # Ubuntu-Server-admin-ssh
[ 2] 69/udp                     ALLOW IN    192.168.10.253
[ 5] 22/tcp                     ALLOW IN    192.168.10.253             # 3850-admin-ssh
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 6] 22/tcp (v6)                ALLOW IN    Anywhere (v6)
```

## Remove the wide-open rule — in the right order

Confirm the scoped rules above actually work *before* removing the
wide-open one, so there's never a moment with zero working SSH rule. From a
trusted machine, open a **new** SSH session without closing the one you're
already using — confirming the new rule works before touching the old one
means a mistake here doesn't lock you out:

```bash
ssh mhubbard@10.100.126.100
```

Once that works, remove the wide-open rule — `Anywhere` in the
`ufw_add_admins.sh` output above, rule `[ 1]` in this example:

```bash
sudo ufw delete 1
```

(Use whatever number the `Anywhere` rule actually shows as — it won't
always be `1`.)

!!! warning "Have a fallback before you start"
    If a typo in the scoped rule locks out every remote session, the
    fallback is the same one [Automating Discovery](appendix-discovery-automation.md#getting-scripts-onoff-the-automation-host)
    already relies on: sit down at the host's own screen (Hyper-V console,
    or physically) and fix the rule from there. Know that's available
    *before* deleting the wide-open rule, not after.
