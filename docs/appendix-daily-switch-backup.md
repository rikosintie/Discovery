# Daily Switch Backup via TFTP and Cisco kron

A lighter-weight alternative to [Automating Discovery](appendix-discovery-automation.md)
for a customer who just wants a daily plaintext copy of every switch's
running-config — no Discovery repo clone, no Python `venv`, no git commits.
It only needs a TFTP server on the automation host and a few lines of
`kron` (Cisco IOS's built-in job scheduler) on each switch.

## Why this exists

Built at a real customer engagement — the same site (`jc`) used throughout
these appendices — before the [Automating Discovery](appendix-discovery-automation.md)
tooling existed. `kron` is IOS-specific, and this approach doesn't discover
anything: no port maps, no MAC/IP tracking over time, just a daily `show
run` backup per switch. For a customer who doesn't want daily git commits
or Python tooling on their automation VM, that's often all they actually
want.

## 1. Install and configure the TFTP server

The server package is `tftpd-hpa` — not `tftp-hpa`, which is the client:

```bash
sudo apt update
sudo apt install tftpd-hpa -y
sudo systemctl enable --now tftpd-hpa
```

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
worth the extra step below: most customers can't navigate to `/srv`, but
they can open **Files** and find `tftp-root` right under their home folder.

Some `tftpd-hpa` packages sandbox the service with `ProtectHome=yes` in
their systemd unit, which makes `/home`, `/root`, and `/run/user`
**completely inaccessible** to the daemon — not a permissions issue, an
outright block, independent of `TFTP_DIRECTORY` or any `in.tftpd` flag.
Check yours before assuming you need to do anything about it:

```bash
grep ProtectHome /usr/lib/systemd/system/tftpd-hpa.service
```

If that prints `ProtectHome=yes`, override it with a drop-in:

```bash
sudo systemctl edit tftpd-hpa
```

Add these two lines in the editor that opens, save, and exit:

```ini
[Service]
ProtectHome=no
```

Then apply it:

```bash
sudo systemctl daemon-reload
sudo systemctl restart tftpd-hpa
```

If the `grep` above prints nothing, or `ProtectHome=no`, skip this override
entirely — a home-directory `TFTP_DIRECTORY` will already work.

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

`add_switches-ufw.sh` handles both requirements from one pass over one
file: it opens port 69/udp (TFTP) for a switch's management IP, so nothing
else on the LAN can reach the TFTP service, and creates + `chmod 777`s that
switch's backup file at the same time. Only 69/udp is needed — TFTP has no
relation to FTP's port 21, despite the similar name.

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

chmod +x add_switches-ufw.sh
./add_switches-ufw.sh tftp-switches.txt
```

----------------------------------------------------------------

Alternatively, open the GUI text editor and create tftp-switches.txt.

----------------------------------------------------------------

`man in.tftpd` only requires the files be *writable* (`666` would satisfy
that), but `777` is what's actually been running in production for years,
so that's what the script uses rather than a theoretical minimum that's
never been tested end-to-end.

!!! note "Why not just add --create instead?"
    `in.tftpd`'s `--create` flag exists specifically to let it write brand
    new files, which sounds like it should remove this whole step. If
    `ProtectHome=yes` turned out to apply and needed the override above,
    that's worth keeping in mind: a home-directory target failing with
    `--create` doesn't mean `--create` is broken, it means `ProtectHome`
    was still blocking the daemon from touching `/home` at all, and no
    `in.tftpd` flag can get around that. Once `/home` is actually
    reachable — whether that took an override or your `tftpd-hpa` build
    never restricted it in the first place — `--create` should genuinely
    remove the need for this step. Worth testing at a low-risk site before
    relying on it, since this hasn't been verified end-to-end here.

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

`check_ufw.sh` and `ufw_audit.sh` both need root — checking UFW's own
status, and (for `ufw_audit.sh`) writing to `/var/log/ufw-check.log`, both
require it:

```bash
sudo ./check_ufw.sh
```

Run without `sudo`, both scripts now fail cleanly instead of printing
partial, confusing output:

```text
$ ./check_ufw.sh
===UFW Service State (systemd)===
This script needs root - run it with sudo.
```

`ufw_audit.sh` appends a timestamped, session-ID'd snapshot to
`/var/log/ufw-check.log` each time it runs — schedule it in cron (root's
crontab, via `sudo crontab -e`) for a running audit trail of whether the
firewall stayed enabled and configured as expected:

```bash
0 6 * * * /path/to/ufw_audit.sh
```
