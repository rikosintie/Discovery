# Automating Discovery

This appendix assumes a small Ubuntu 26.04 desktop VM at the customer site —
not your own Windows workstation — that runs Discovery unattended on a
schedule. Everything below (`bash`, `cron`, the Python `venv`, `git`) runs on
that VM, typically reached over SSH from your own laptop.

| | |
|---|---|
| Hostname | `discover` |
| Username | `mhubbard` |
| IP address | `10.100.126.100` |
| OS | Ubuntu 26.04 Desktop (on Hyper-V) |

If the customer doesn't already have one, stand up an Ubuntu 26.04 desktop VM first replacing `mhubbard`, `discover`, and `10.100.126.100` with values for your customer.

Install the following on the VM.

- sudo apt update - Update the package repositories before installing
- git - `sudo apt install git`
- python3- `sudo apt install python3`
- python3-venv - `sudo apt install python3-venv`
- snmp - `sudo apt install snmp`

 then clone the Discovery repo and follow the setup in [Getting Started](Getting_Started.md).

Some steps below (the `SNMP_COMMUNITY` variable and the `snmp_arp_cache.py`
line in the wrapper script) are only needed if the site also has a firewall
whose ARP table you're pulling — see [Polling a Firewall's ARP Table via SNMP](appendix-firewall-arp-snmp.md).

Skip those specific pieces if not; everything else in this appendix applies
regardless.

----------------------------------------------------------------

## Credential handling for scripts

Never hardcode credentials in a script. Two solid patterns:

- **Environment variables** loaded from a file readable only by the running
  user (`chmod 600`), sourced by the script or loaded via `python-dotenv`
- **OS keyring** (the `keyring` Python library) for interactive/dev-laptop
  use — stores secrets in the OS credential store instead of a plaintext file

Either way, this is about the password presented *to the switch or firewall*
— a read-only SNMP community string, or an API key scoped to a monitoring
role where the device's firmware supports it — not the automation host's own
OS account. There's nothing to choose on the Ubuntu side: every example in
these appendices runs as the one `mhubbard` account created during setup,
and Ubuntu disables the root login by default anyway.

----------------------------------------------------------------

## Getting scripts on and off the automation host

The Discovery scripts themselves arrive via `git clone` — you won't normally
need to copy those by hand. But you'll still occasionally need to move a
one-off file between your laptop and the automation host: a site-specific
data file before the repo is fully set up, or a log/data file you want to
look at locally afterward. `scp` (secure copy, built on SSH) handles both
directions from a single command line.

Two machines, two IPs — easy to mix up on site. Example values from a real
engagement:

| | |
|---|---|
| Host (automation VM) | `10.100.126.100` |
| Laptop | `10.100.126.110` |

**Laptop → host** (push) — run this from your laptop, `10.100.126.110`, for
example, copying a device-inventory CSV you built while scoping the site
onto the VM before the first run:

```bash
scp device-inventory-cust1.csv mhubbard@10.100.126.100:~/Documents/Discovery/
```

**Host → laptop** (pull) — also run from your laptop, `10.100.126.110`; `scp`
has no way to reach out from the host uninvited, so the pull direction is
still a command you type on the laptop, just with source and destination
swapped. For example, copying today's log back to your laptop to review
locally:

```bash
scp mhubbard@10.100.126.100:~/discovery-daily.log .
```

`scp SOURCE DESTINATION` — whichever side has the `user@host:` prefix is the
remote end (the automation host, `10.100.126.100`); the side without it is
wherever you're running the command from (your laptop). The trailing `.` in
the pull example means "into my current directory."

!!! Note "Windows 11"
    `scp` ships built into Windows 11 as part of the OpenSSH client — no
    install needed. Open PowerShell or Windows Terminal and the same two
    commands above work as-is.

    If you're on an older Windows 10 build without OpenSSH, or you'd rather
    have a drag-and-drop GUI — the same kind of tool many network engineers
    already use for firmware uploads — install
    [WinSCP](https://winscp.net/eng/download.php): open a new **SFTP**
    session to `10.100.126.100` with the `mhubbard` credentials, then drag
    files between the local and remote panes in either direction.

## Daily automation (customer site example)

Originally scheduled weekly, later switched to daily once it was confirmed
the customer site (8 Cisco 2960X switches, ~96 MAC addresses, VM directly
fiber-connected to the core over 10Gb DAC) has no meaningful load concern
either way, and daily granularity on the MAC table / port maps is more
useful for catching device moves close to when they happen.

Wrapper script (`~/discovery-daily.sh`) that sources credentials, activates
the venv, runs the pull/merge/map sequence, commits results to a local git
repo, and records a last-run status line:

### Create the shell script

The wrapper script lives directly in the home directory — not inside the
Discovery repo folder itself — since it's a personal utility rather than
part of the versioned codebase, and that's the path the crontab entry below
expects:

```bash
cd ~
touch discovery-daily.sh
nano discovery-daily.sh
```

Paste the following into nano, then `ctrl+o` to save, `ctrl+x` to close it:

```bash
#!/bin/bash
set -e

source ~/.config/discovery/cyberark.env
cd ~/Documents/Discovery
source venv/bin/activate

python3 snmp_arp_cache.py  # only if this site has a firewall to poll
python3 config-pull.py -s jc-4500
python3 config-pull.py -s jcedge
python3 arp.py -s jcedge -c jc-core
python3 merge-sonicwall-arp.py -c jc-core  # only if this site has a firewall to poll
python3 port-map.py -s jcedge -c jc-core -d 10.100.126.6

deactivate

git add .
git diff --cached --quiet || git commit -m "Daily discovery run $(date '+%Y-%m-%d %H:%M')"

echo "$(date '+%Y-%m-%d %H:%M') - run completed, exit $?" >> ~/discovery-last-run.txt
```

(`-c jc-core` on the merge step is this customer's core switch name, matching
`arp.py`'s `-c` value — adjust it per site. See
[Polling a Firewall's ARP Table via SNMP](appendix-firewall-arp-snmp.md) for
the SonicWall/FortiGate setup that feeds `snmp_arp_cache.py`.)

### Make discovery-daily.sh executable

```bash
chmod +x discovery-daily.sh
ls -l discovery-daily.sh # should see -rwxr-xr-x
```

The `git diff --cached --quiet ||` guard skips the commit (rather than
erroring under `set -e`) on runs where nothing changed.

Note: because of `set -e`, if any Python script earlier in the sequence
fails, the whole script exits immediately and the final `echo` line never
runs — so a missing entry in `discovery-last-run.txt` is itself the failure
signal, not just a silent gap.

### Create a credentials file

Credentials file (`~/.config/discovery/cyberark.env`, `chmod 600`) — the
variable name is a holdover from a prior CyberArk-integrated environment and
isn't tied to any actual vault here, just a plain exported value:

```bash
mkdir -p ~/.config/discovery
cat > ~/.config/discovery/cyberark.env << 'EOF'
export cyberARK=the_actual_password
export SNMP_COMMUNITY=the_actual_community_string
export FIREWALL_HOST=10.100.126.1
EOF
chmod 600 ~/.config/discovery/cyberark.env
```

(`SNMP_COMMUNITY` and `FIREWALL_HOST` are only needed if this site has a
firewall you're polling for ARP data — see
[Polling a Firewall's ARP Table via SNMP](appendix-firewall-arp-snmp.md).
`snmp_arp_cache.py` has no hardcoded default IP, so `FIREWALL_HOST` must be
set to whatever this customer's firewall actually is.)

View the file:

```bash
cat ~/.config/discovery/cyberark.env
```

You should see:

```bash
export cyberARK=the_actual_password
export SNMP_COMMUNITY=the_actual_community_string
export FIREWALL_HOST=10.100.126.1
```

### Create the schedule

Crontab entry (daily at 18:00):

```bash
crontab -e
```

An editor will open, scroll to the bottom and paste this in:

```bash
0 18 * * * /home/mhubbard/discovery-daily.sh >> /home/mhubbard/discovery-daily.log 2>&1
```

## Git repo

- If Discovery was `git clone`d from a public GitHub repo, remove the
  inherited remote and history before running on customer data. This
  prevents customer data from accidentally being pushed back to the public
  repo:

  ```bash
  cd ~/Documents/Discovery
  rm -rf .git
  git init
  git add .
  git commit -m "Initial commit"
  ```

- Set local commit identity to the site account rather than a personal name.
  The `@localhost` is used since the VM isn't going to be sending email:

  ```bash
  git config --global user.name "mhubbard"
  git config --global user.email "mhubbard@localhost"
  ```

- `.gitignore` should exclude the venv, Python cache, and (if it were ever
  placed inside the repo — it shouldn't be) the credentials file:

  ```bash
  cd ~/Documents/Discovery
  nano .gitignore
  ```

  Paste the following into the `.gitignore` file:

  ```bash
  venv/
  __pycache__/
  *.pyc
  cyberark.env
  ```

- Confirm no remote is configured, so a stray `git push` can't send customer
  network data anywhere:

  ```bash
  git remote -v   # should return nothing
  ```

## Log rotation

Daily cron output grows fast. Create a `logrotate` file to compress and
delete old entries.

Create the `logrotate` config:

```bash
sudo nano /etc/logrotate.d/discovery-daily
```

Paste this into nano:

```bash
/home/mhubbard/discovery-daily.log {
    daily
    rotate 12
    compress
    missingok
    notifempty
    copytruncate
    su mhubbard mhubbard
}
```

The `su mhubbard mhubbard` directive is required when the log's parent
directory is owned by a non-root user — logrotate (run as root via cron)
otherwise refuses to rotate it, citing insecure parent-directory permissions.
`su` tells logrotate to act as that user instead, sidestepping the check.

Test manually:

```bash
sudo logrotate -f /etc/logrotate.d/discovery-daily
```

**Rotation timing vs. verifying the job ran:** on modern Ubuntu, logrotate
runs via a systemd timer, not plain cron — by default `OnCalendar=daily`
(around midnight) with a 12-hour accuracy window, so it can fire anywhere
from midnight to noon.

Check the actual schedule on a given box with:

```bash
systemctl list-timers logrotate.timer
```

With `copytruncate`, rotation zeroes the live log file. Since the discovery
script runs at 18:00 and rotation happens sometime between midnight and
noon, the live `discovery-daily.log` will read empty for most of the day —
that's expected, not a sign the job failed. Don't rely on tailing the live
log alone to confirm the job is working; instead:

- Check `~/discovery-last-run.txt` (see wrapper script above) — a plain
  timestamp line untouched by log rotation
- Check git commit history/timestamps in the Discovery repo — a real proof
  of execution independent of the log entirely
- Check already-rotated logs when the live one is empty:
  `zcat discovery-daily.log.1.gz | tail -50`
- Confirm cron actually fired it:
  `journalctl -u cron --since "1 day ago" | grep discovery-daily`

## Testing a cron job without waiting for its real schedule

Temporarily set the crontab entry a couple of minutes ahead, for example, to
run at 18:05:

```bash
crontab -e
5 18 * * * /home/mhubbard/discovery-daily.sh >> /home/mhubbard/discovery-daily.log 2>&1
```

then:

```bash
tail -f /home/mhubbard/discovery-daily.log       # watch script output live
journalctl -u cron -f                            # confirm cron actually fired it
watch -n 1 'ps aux | grep -E "config-pull|arp.py|merge-sonicwall|port-map"'  # optional
```

Revert to the real schedule once confirmed.
