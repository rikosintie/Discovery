## Appendix: SonicWall ARP Cache Export & Discovery Automation

### Background

SonicOS 7.x's GUI ARP Cache page (**Network > ARP > ARP Cache**) does not include an Export button in current firmware builds — that feature existed in the older SonicOS 6.5 UI but was dropped. The CLI doesn't help either: `show arp` returns the ARP *configuration* stanza (`timeout`, `glean`) rather than the live dynamic table, since SonicOS's CLI is primarily a configuration interface, not a diagnostics one.

For a one-off pull of a handful of entries, the fastest path is a manual copy/paste out of the browser table. For repeatable, scriptable access, the two real options are:

- **SNMP** — poll the standard ARP MIB (`ipNetToMediaTable`, OID `1.3.6.1.2.1.4.22`)
- **SonicOS REST API** — enable under **Device | Settings | Administration | SonicOS API**;
  authenticate against `POST /api/sonicos/auth`, then query the appropriate endpoint
  (the exact ARP monitoring path isn't clearly documented — check the API browser/explorer
  linked from that same settings page, or use the generic `POST /api/sonicos/direct/cli`
  endpoint to push a raw CLI command and get JSON back)

### SNMP quick start

Here's the SonicOS 7.X path — you'll do this on the **LAN to LAN** matrix (self-management traffic on the LAN zone), same pattern SonicWall uses for restricting WAN management, just applied to LAN instead.

**1. Enable SNMP as a service**
- **Device | Settings | SNMP** → check **Enable SNMP** → **Accept**
- Click **Configure** and set your Get Community Name (and Trap Community/host if you want traps) → **OK**

**2. Enable SNMP on the LAN (X0) interface**
- **Network | System | Interfaces** → edit **X0**
- In the **Management** section, check **SNMP** → **OK**

This step auto-generates a management access rule allowing SNMP to the firewall's LAN IP — by default with Source = Any, which is the part you want to lock down.

**3. Create an address object for 10.100.126.100**
- **Object | Address Objects | Add**
- Name it something like `ubuntu-snmp-poller`, Zone Assignment: **LAN**, Type: **Host**, IP: `10.100.126.100`

**4. Restrict the management rule's source**
- **Policy | Rules and Policies | Access Rules**
- Switch view style to **Matrix**, click the **LAN to LAN** cell
- Find the auto-added SNMP management rule, click **Configure**
- Change **Source** from **Any** to your new `ubuntu-snmp-poller` address object → **OK**

That last step is the actual restriction — everything else is just turning SNMP on. Once that source field is scoped, only 10.100.126.100 will be able to reach SNMP on the firewall; anything else on 10.100.126.0/24 hitting UDP 161 gets denied by default, since SonicOS denies non-matching traffic on management rules by default.

One thing worth deciding before you do this tomorrow: SonicOS 7 supports SNMPv3 as well as v1/v2c — v2c (what the community-string flow above sets up) is simplest to script against, but sends the community string in cleartext. In this case, snmp v2c scoped to a single source IP is a reasonable tradeoff since the snmp is only on the wire between the server and the SonicWall.

----------------------------------------------------------------

Install the client tools:

```bash
sudo apt update
sudo apt install snmp -y
```

SNMP: if you have SNMP enabled on the box, you could poll the standard ARP MIB
(ipNetToMediaTable / .1.3.6.1.2.1.4.22) from a Linux box with snmpwalk — this would actually get you clean scriptable output

scp -rp merge-sonicwall-arp.py  mhubbard@10.100.126.100:/home/mhubbard/Documents/04_tools/Discovery

python3 config-pull.py -s jc-4500
python3 config-pull.py -s jcedge
python3 arp.py -s jcedge -c jc-core
python3 merge-sonicwall-arp.py
python3 port-map.py -s jcedge -c jc-core -d 10.100.126.6

Pull the ARP table:

```bash
snmpwalk -v2c -c <community_string> <firewall_ip> 1.3.6.1.2.1.4.22
```

### Enabling SSH on the TZ370

SSH management is off by default per-interface:

1. **Network > Interfaces** → edit the interface owning the management IP
2. **Management** section → toggle **SSH** on
3. **OK**

If connecting from a different zone/VLAN than the target interface, an access rule
permitting SSH traffic from that source zone may also be required.

### Credential handling for scripts

Never hardcode credentials in a script. Two solid patterns:

- **Environment variables** loaded from a file readable only by the running user
  (`chmod 600`), sourced by the script or loaded via `python-dotenv`
- **OS keyring** (the `keyring` Python library) for interactive/dev-laptop use —
  stores secrets in the OS credential store instead of a plaintext file

Either way, use a dedicated low-privilege account for API/SNMP access rather than
an admin account, where the firmware supports scoped roles.

### Discovery daily automation (customer site example)

Originally scheduled weekly, later switched to daily once it was confirmed the
customer site (8 Cisco 2960X switches, ~96 MAC addresses, VM directly fiber-connected to the core over 10Gb DAC) has no meaningful load concern either way, and daily granularity on the MAC table / port maps is more useful for catching device moves close to when they happen.

Wrapper script (`/path/to/discovery-weekly.sh`) that sources credentials, activates the venv, runs the pull/merge/map sequence, commits results to a local git repo, and records a last-run status line:

#### Create the shell script

```bash
cd /path/to/Discovery
touch discovery-weekly.sh
nano discovery-weekly.sh
```

Paste the following into nano, then `ctrl_s` to save, `ctrl+x` to close it.

```bash
#!/bin/bash
set -e

source ~/.config/discovery/cyberark.env
cd /path/to/Discovery
source Discovery/bin/activate

python3 config-pull.py -s jc-4500
python3 config-pull.py -s jcedge
python3 arp.py -s jcedge -c jc-core
python3 merge-sonicwall-arp.py
python3 port-map.py -s jcedge -c jc-core -d 10.100.126.6

deactivate

git add .
git diff --cached --quiet || git commit -m "Discovery run $(date '+%Y-%m-%d %H:%M')"

echo "$(date '+%Y-%m-%d %H:%M') - run completed, exit $?" >> ~/discovery-last-run.txt
```

----------------------------------------------------------------

#### Make discovery-weekly.sh executable

```bash
chmod +x discovery-weekly.sh
ls -l discovery-weekly.sh # should see .rwxr-xr-x
```

The `git diff --cached --quiet ||` guard skips the commit (rather than erroring under
`set -e`) on runs where nothing changed.

Note: because of `set -e`, if any Python script earlier in the sequence fails, the whole script exits immediately and the final `echo` line never runs — so a missing entry in `discovery-last-run.txt` is itself the failure signal, not just a silent gap.

#### Create a credentials file

Credentials file (`~/.config/discovery/cyberark.env`, `chmod 600`) — the variable name is a holdover from a prior CyberArk-integrated environment and isn't tied to any actual vault here, just a plain exported value:

```bash
mkdir -p ~/.config/discovery
cat > ~/.config/discovery/cyberark.env << 'EOF'
export cyberARK=the_actual_password
export SNMP_COMMUNITY=the_actual_community_string
EOF
chmod 600 ~/.config/discovery/cyberark.env
```

View the file

```bash
cat ~/.config/discovery/cyberark.env
```

You should see

```bash
export cyberARK=the_actual_password
export SNMP_COMMUNITY=the_actual_community_string
```

----------------------------------------------------------------

#### Create the schedule

Crontab entry (daily at 18:00):

Run the following:

```bash
crontab -e
```

An editor will open, scroll to the bottom and paste this in:

```bash
0 18 * * * /home/mhubbard/discovery-weekly.sh >> /home/mhubbard/discovery-weekly.log 2>&1
```

----------------------------------------------------------------

### Git repo

- If Discovery was `git clone`d from a public GitHub repo, remove the inherited
remote and history before running on customer data. This prevents customer data from accidentally be pushed back to my public repo:

  ```bash
  cd /path/to/Discovery
  rm -rf .git
  git init
  git add .
  git commit -m "Initial commit"
  ```

- Set local commit identity to the site account rather than a personal name. The `@localhost` is used since the VM isn't going to be sending email:

  ```bash
  git config --global user.name "mhubbard"
  git config --global user.email "mhubbard@localhost"
  ```

- `.gitignore` should exclude the venv, Python cache, and (if it were ever placed inside the repo — it shouldn't be) the credentials file:

```bash
cd /path/to/Discovery
nano .gitignore
```

Paste the following into the `.gitignore` file

```bash
Discovery/
__pycache__/
*.pyc
cyberark.env
```

- Confirm no remote is configured, so a stray `git push` can't send customer network data anywhere:

```bash
git remote -v   # should return nothing
```

### Log rotation

Daily cron output grows fast. Create a `logrotate` file to compress and delete entries

Create the `logrotate` config:

```bash
sudo nano /etc/logrotate.d/discovery-weekly
```

Paste this into nano:

```bash
/home/mhubbard/discovery-weekly.log {
    daily
    rotate 12
    compress
    missingok
    notifempty
    copytruncate
    su mhubbard mhubbard
}
```

The `su mhubbard mhubbard` directive is required when the log's parent directory is owned by a non-root user — logrotate (run as root via cron) otherwise refuses to rotate it, citing insecure parent-directory permissions. `su` tells logrotate to act as that user instead, sidestepping the check.

Test manually:

```bash
sudo logrotate -f /etc/logrotate.d/discovery-weekly
```

**Rotation timing vs. verifying the job ran:** on modern Ubuntu, logrotate runs via a systemd timer, not plain cron — by default `OnCalendar=daily` (around midnight) with a 12-hour accuracy window, so it can fire anywhere from midnight to noon.

Check the actual schedule on a given box with:

```bash
systemctl list-timers logrotate.timer
```

With `copytruncate`, rotation zeroes the live log file. Since the discovery script runs at 18:00 and rotation happens sometime between midnight and noon, the live `discovery-weekly.log` will read empty for most of the day — that's expected, not a sign the job failed. Don't rely on tailing the live log alone to confirm the job is working; instead:

- Check `~/discovery-last-run.txt` (see wrapper script above) — a plain timestamp
  line untouched by log rotation
- Check git commit history/timestamps in the Discovery repo — a real proof of execution independent of the log entirely
- Check already-rotated logs when the live one is empty: `zcat discovery-weekly.log.1.gz | tail -50`
- Confirm cron actually fired it: `journalctl -u cron --since "1 day ago" | grep discovery-weekly`

### Testing a cron job without waiting for its real schedule

Temporarily set the crontab entry a couple of minutes ahead,

for example, to run at 18:05:

```bash
contab -e
5 18 * * * /home/mhubbard/discovery-weekly.sh >> /home/mhubbard/discovery-weekly.log 2>&
```

then:

```bash
tail -f /home/mhubbard/discovery-weekly.log       # watch script output live
journalctl -u cron -f                            # confirm cron actually fired it
watch -n 1 'ps aux | grep -E "config-pull|arp.py|merge-sonicwall|port-map"'  # optional
```

Revert to the real schedule once confirmed.
