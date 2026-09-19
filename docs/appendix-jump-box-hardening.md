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

Two equivalent patterns — pick whichever matches the site:

**A dedicated management subnet**, if one exists:

```bash
sudo ufw allow from 10.100.100.0/24 to any port 22 proto tcp
```

**A short list of trusted hosts**, if it doesn't — your own laptop, and
maybe an MSP's jump host:

```bash
sudo ufw allow from 10.100.126.110 to any port 22 proto tcp comment 'admin laptop'
```

(`10.100.126.110` is the same laptop IP used as the example throughout
[Automating Discovery](appendix-discovery-automation.md#getting-scripts-onoff-the-automation-host).)
The `comment` is optional but worth adding — `sudo ufw status verbose` will
show it, which matters once there's more than one narrow rule to remember
the reason for.

## Remove the wide-open rule — in the right order

Add the scoped rule and confirm it works *before* removing the wide-open
one, so there's never a moment with zero working SSH rule:

```bash
sudo ufw allow from 10.100.126.110 to any port 22 proto tcp
sudo ufw reload
```

From the trusted machine, open a **new** SSH session without closing the
one you're already using — confirming the new rule actually works before
touching the old one means a mistake here doesn't lock you out:

```bash
ssh mhubbard@10.100.126.100
```

Once that works, find and remove the wide-open rule:

```bash
sudo ufw status numbered
```

```text
     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere
[ 2] 22/tcp                     ALLOW IN    10.100.126.110
```

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
