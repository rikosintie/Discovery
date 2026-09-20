# Daily Switch Backup via TFTP and Cisco kron

A lighter-weight alternative to [Automating Discovery](appendix-discovery-automation.md)
for a customer who just wants a daily plaintext copy of every switch's
running-config — no Discovery repo clone, no Python `venv`, no git commits.
It only needs a TFTP server on the automation host and a few lines of
`kron` (Cisco IOS's built-in job scheduler) on each switch.

----------------------------------------------------------------

## Why this exists

Built at a real customer engagement — the same site (`jc`) used throughout
these appendices — before the [Automating Discovery](appendix-discovery-automation.md) tooling existed. `kron` is IOS-specific, and this approach doesn't discover anything: no port maps, no MAC/IP tracking over time, just a daily `show run` backup per switch. For a customer who doesn't want daily git commits or Python tooling on their automation VM, that's often all they actually want.

This VM is a good candidate to become a jump box — see
[Restricting SSH on the Automation Host](appendix-jump-box-hardening.md).
Restricting logins to a management subnet or a short trusted-host list,
instead of leaving SSH open to the whole network, is worth doing here even
if the customer never runs the full
[Automating Discovery](appendix-discovery-automation.md) setup. For a
customer working toward CMMC, or similar compliance requirements,
this is a reasonable first step — not the whole story, but a real one.

[Termius](https://docs.termius.com/) (subscription required) is worth a
mention as a client — it makes managing switches and servers a
more pleasant experience than juggling separate terminal windows. The subscription gives you the ability to instal; `Termius` on:

- Windows
- Mac
- Linux
- IOS
- Android

It's great if you are in a closet and need to make a quick change and only have your phone with you!

----------------------------------------------------------------

## Set up the VM

This appendix assumes a small Ubuntu 26.04 desktop VM at the site — not
your own Windows workstation. Hyper-V, ESXi, KVM, Proxmox — doesn't matter
what hosts it.

Here is an example:

- **OS**: Ubuntu 26.04 Desktop (on Hyper-V)
- **Hostname:** Discover
- **IP address**: 10.100.126.100
- **Username**: mhubbard

If the customer doesn't already have one, stand up an Ubuntu 26.04 desktop
VM first, replacing `mhubbard`, `discover`, and `10.100.126.100` with
values for your customer.

Open a terminal, `ctrl+alt+t`, then update the package repositories:

```bash
sudo apt update
```

If this is a new install you'll probably see packages that need updating
once that finishes:

```bash
sudo apt upgrade -y
```

Install `openssh-server` for remote management — not included in an
Ubuntu Desktop install by default:

```bash
sudo apt install openssh-server -y
```

## 1. Install and configure the TFTP server

The server package is `tftpd-hpa` — not `tftp-hpa`, which is the client:

```bash
sudo apt update
sudo apt install tftpd-hpa -y
```

Some `tftpd-hpa` packages sandbox the service with `ProtectHome=yes` in
their systemd unit, which makes `/home`, `/root`, and `/run/user`
**completely inaccessible** to the daemon — not a permissions issue, an
outright block, independent of `TFTP_DIRECTORY` or any `in.tftpd` flag.
Check this — and fix it if needed — before enabling the service, so it
only ever starts once, already configured correctly:

```bash
sudo systemctl edit tftpd-hpa
```

On Ubuntu 26.04 this opens an editor with a blank area at the top to type
into, followed by a large read-only reference dump of the unit's current
settings — including a `# ProtectHome=yes` line — clearly marked as
existing only for reference. **Don't edit anything in that reference
section** — `systemctl` detects changes made there as "modifications
outside of the staging area," discards them, and if that leaves the actual
editable area empty, cancels the whole edit without writing anything
(confirmed the hard way: editing that line in place produced exactly that
error and silently wrote nothing).

Instead, type a brand new override into the blank area at the top:

```ini
[Service]
ProtectHome=no
```

Save and exit — `systemctl edit` reloads the unit automatically, no
separate `daemon-reload` needed.

If `ProtectHome` doesn't appear anywhere in that reference dump, close
without saving — a home-directory `TFTP_DIRECTORY` will already work,
nothing to override.

Config file is `/etc/default/tftpd-hpa`:

```bash
sudo nano /etc/default/tftpd-hpa
```

```text
TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/home/mhubbard/tftp-root"
TFTP_ADDRESS=":69"
TFTP_OPTIONS="--secure"
```

Use the real absolute path here, not a literal `~` — systemd never expands
that regardless of directory. A customer-facing home-directory location is
worth the override above: most customers can't navigate to `/srv`, but
they can open **Files** and find `tftp-root` right under their home folder.

Now enable and start the service:

```bash
sudo systemctl enable --now tftpd-hpa
```

Confirm it's running:

```bash
systemctl status tftpd-hpa
```

## 2. Open the firewall and pre-create each switch's backup file

TFTP has to have an existing filename with the correct permissions before
it will write to it — confirmed straight from `man in.tftpd`:

> By default, tftpd will only allow upload of files that already exist ...
> Files may be written only if they already exist and are publicly
> writable, unless the `--create` option is specified.

`ufw_add_switches.sh` handles both requirements from one pass over one
file: it opens port 69/udp (TFTP) for a switch's management IP, so nothing
else on the LAN can reach the TFTP service, and creates + `chmod 666`s that
switch's backup file at the same time. Only 69/udp is needed — TFTP has no
relation to FTP's port 21, despite the similar name.

There's no repo to clone this out of, so create it directly:

```bash
cd ~
touch ufw_add_switches.sh
nano ufw_add_switches.sh
```

Paste the following into nano, then `ctrl+o` to save, `ctrl+x` to close it:

```bash
#!/bin/bash
# Open UFW for TFTP (port 69/udp) from a list of switch management IPs, and
# pre-create the matching TFTP backup file (chmod 666) for each one so the
# first kron push doesn't fail on a missing file.
#
# Reads "ip,filename" pairs from tftp-switches.txt (one per line, blank
# lines and lines starting with # ignored) so a customer never has to edit
# this script itself, just the IP/filename list.

set -e

FILE="${1:-tftp-switches.txt}"
TFTP_ROOT="${TFTP_ROOT:-$HOME/tftp-root}"

if [[ ! -f "$FILE" ]]; then
  echo "Missing $FILE - create it with one 'ip,filename' pair per line" >&2
  exit 1
fi

# A brand-new Ubuntu install ships ufw installed but inactive. Allow SSH
# before enabling it so this doesn't cut off a remote session running over
# the same connection that's executing this script. --force skips ufw's
# interactive "this may disrupt existing ssh connections" confirmation,
# which would otherwise hang a non-interactive run.
sudo ufw allow ssh
sudo ufw --force enable

while IFS=',' read -r ip filename; do
  ip="$(echo "$ip" | xargs)"
  [[ -z "$ip" || "$ip" == \#* ]] && continue
  filename="$(echo "$filename" | xargs)"
  if [[ -z "$filename" ]]; then
    echo "Missing filename for $ip in $FILE - each line needs 'ip,filename'" >&2
    exit 1
  fi

  sudo ufw allow from "$ip" to any port 69 proto udp
  touch "$TFTP_ROOT/$filename"
  chmod 666 "$TFTP_ROOT/$filename"
done < "$FILE"

# Reload rules to apply
sudo ufw reload

# Show the resulting ruleset, rules sorted numerically by source IP.
# Capturing to a variable first, rather than piping head and tail off the
# same stream, avoids head consuming input tail still needs - a real,
# reproducible gotcha when both read from one pipe. Named ufw_status rather
# than status, since status is a read-only special variable in zsh (aliases
# $?) - fine under this script's own #!/bin/bash, but a landmine if it's
# ever sourced into a zsh shell instead of executed.
#
# Sorting by a fixed field number (e.g. sort -k6,6) doesn't work: ufw right
# -pads single-digit rule numbers with a space ("[ 4]", two tokens) but not
# double-digit ones ("[10]", one token), so every field after it shifts by
# one once rule numbers reach 10 - confirmed on a real box with 16 rules.
# Finding whichever field actually looks like an IPv4 address sidesteps
# that entirely, regardless of rule-number width.
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
chmod +x ufw_add_switches.sh
```

That `sudo ufw allow ssh` inside the script is deliberately wide open —
just enough to guarantee `ufw enable` doesn't lock out the session running
it. Once everything below is working, see
[Restricting SSH on the Automation Host](appendix-jump-box-hardening.md) to
scope that down; the TFTP rules this script adds are already
per-switch-IP, but SSH is left open to the whole LAN until that's done.

Both come from `tftp-switches.txt` — `ip,filename` pairs, one per line,
blank lines and `#` comments ignored — so a customer never has to edit the
script itself, just this list:

```bash
cat > tftp-switches.txt << 'EOF'
10.100.126.253,JC-core.wri
10.100.126.236,JC-IDF-1.wri
10.100.126.237,JC-IDF-2.wri
10.100.126.242,JC-IDF-CAM-1.wri
10.100.126.231,JC-MDF-1.wri
10.100.126.232,JC-MDF-2.wri
10.100.126.243,JC-MDF-3.wri
10.100.126.235,JC-MDF-4.wri
10.100.126.241,JC-MDF-CAM-1.wri
10.100.126.238,JC-MDF-CAM-2.wri
10.100.126.244,JC-SPARE.wri
EOF

./ufw_add_switches.sh tftp-switches.txt
```

----------------------------------------------------------------

Alternatively, open the GUI text editor and create tftp-switches.txt.

----------------------------------------------------------------

```bash linenums='1' hl_lines='1'
sudo ./ufw_add_admins.sh ufw-admins.txt
```

----------------------------------------------------------------

```bash title='Command Output'
Rule added
Rule added
Rule added
Firewall reloaded
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

----------------------------------------------------------------

!!! note
    Notice that the `ssh any` is gone. If you are running this over ssh, make sure the device you are on is in the list or you will be locked out.

Now you can use the `ufw_check.sh` script to view the tftp and ssh rules:

```bash linenums='1' hl_lines='1'
sudo ./ufw_check.sh
```

```bash title='Command Output'
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

----------------------------------------------------------------

`man in.tftpd` only requires the files be *writable*, and `666` is what
the script uses — confirmed working in production, not just the
theoretical minimum from the man page. It also doesn't set the execute
bit `777` would, which these plaintext config backups never need.

!!! note "Why not just add --create instead?"
    `in.tftpd`'s `--create` flag exists specifically to let it write brand
    new files, which sounds like it should remove this whole step — and
    once the `ProtectHome=no` override above is in place, it genuinely
    would (confirmed on a fresh Ubuntu 26.04 install). The reason to skip
    it anyway is security, not uncertainty: without `--create`, TFTP can
    only ever *overwrite* one of the specific files pre-created here — it
    can't be handed a brand new filename by anyone who reaches port 69.
    A switch inventory is fairly static, so pre-creating one file per
    switch, once, is cheap insurance against an unlikely but real class of
    attack: something on the LAN pushing an arbitrary file to this host
    under a name nothing here is watching for.

If this same automation host also runs the git-based
[Automating Discovery](appendix-discovery-automation.md) setup, add
`tftp-switches.txt` to `.gitignore` alongside `vlans.txt` — it's
site-specific data, not something to commit.

## 3. Schedule the backup on each switch (Cisco kron)

```text
kron occurrence WrConfig_Job at 22:30 recurring
 policy-list Write_Config
!
kron policy-list Write_Config
 cli wr mem
 cli show run | redirect tftp://10.100.126.100/JC-MDF-1.wri
!
```

- `kron occurrence <name> at <time> recurring` — schedules a named job daily
  at that time.
- `policy-list <name>` under the occurrence — which set of commands to run.
- `kron policy-list <name>` defines that set: `cli wr mem` saves the running
  config to NVRAM first (so a reload before the next backup doesn't lose
  in-flight changes), then `cli show run | redirect tftp://<host>/<file>`
  pushes the running-config text straight to the TFTP server.

Repeat per switch with the matching filename from step 2, and a distinct
occurrence name if you'd rather not have every switch push in the same
second.

## 4. Verify and monitor

One script, `ufw_check.sh`, covers both an ad-hoc interactive check and a
scheduled audit trail — without `--log`, it just prints UFW's current state; with `--log`, it also appends a timestamped, session-ID'd snapshot to
`/var/log/ufw-check.log`. Create it the same way:

```bash
cd ~
touch ufw_check.sh
nano ufw_check.sh
```

```bash
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

# Show the actual ruleset too, not just the summary above - sorted
# numerically by source IP rather than by ufw's own rule numbers. Same
# approach as ufw_add_switches.sh: ufw right-pads single-digit rule
# numbers with a space ("[ 4]", two tokens) but not double-digit ones
# ("[10]", one token), so a fixed field number shifts once rule numbers
# reach 10 - finding whichever field looks like an IPv4 address sidesteps
# that regardless of rule-number width.
echo
ufw_status="$(ufw status numbered)"
echo "$ufw_status" | head -4
echo "$ufw_status" | tail -n +5 | awk '{
  key = ""
  for (i = 1; i <= NF; i++) {
    if ($i ~ /^[0-9]{1,3}(\.[0-9]{1,3}){3}$/) { key = $i; break }
  }
  print key "\t" $0
}' | sort -k1,1 -V | cut -f2-

if $log_mode; then
  {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Session $session_id"
    echo "  Service enabled: $svc_enabled"
    echo "  Service state  : $svc_state"
    echo "  Firewall state : $fw_state"
    echo "----------------------------------------"
  } >> "$LOGFILE"
fi
```

```bash
chmod +x ufw_check.sh
```

It needs root either way — checking UFW's own status, and (with `--log`)
writing to `/var/log/ufw-check.log`, both require it:

```bash
sudo ./ufw_check.sh
```

```bash title='Command Output'
===UFW Service State (systemd)===
Service enabled: enabled
Service state  : active
Firewall state : Status: active

Status: active

     To                         Action      From
     --                         ------      ----
[ 2] 69/udp                     ALLOW IN    192.168.10.253
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 3] 22/tcp (v6)                ALLOW IN    Anywhere (v6)
```

----------------------------------------------------------------

Prints the service/firewall summary followed by the actual ruleset — the
log file only ever gets the summary lines, not a full rule dump each run,
to keep it from growing unbounded on a frequent cron schedule.

Run without `sudo`, it fails cleanly instead of printing partial, confusing
output:

```text
$ ./ufw_check.sh
This script needs root - run it with sudo.
```

For a running audit trail, schedule the `--log` form in cron (root's
crontab, via `sudo crontab -e`):

```bash
0 6 * * * /path/to/ufw_check.sh --log
```
