## Appendix: SNMP-Based ARP Cache Polling for SonicWall Firewalls

### Why

`arp.py`/`config-pull.py` already capture MAC/ARP data for zones that transit
the managed switch fabric (e.g. LAN, Surveillance). Zones that terminate
directly on the firewall — WAN, DMZ, Guest, Voice, and similar — aren't visible
to the switches at all, so they never showed up in `merge-sonicwall-arp.py`'s
output. Polling the firewall's own ARP table via SNMP fills that gap.

This assumes SNMP has already been enabled and scoped to a single polling
host on the firewall — see [SonicWall TZ370 — SNMP Setup with Restricted
Source Access](sonicwall-snmp-setup.md) for those steps.

### The script

`snmp_arp_cache.py` walks the standard ARP MIB (`ipNetToMediaTable`,
`1.3.6.1.2.1.4.22`) via `snmpwalk` and writes `tz370_arp_cache.csv` in the
same 5-column format `merge-sonicwall-arp.py` already expects
(`IP Address,Type,MAC Address,Vendor,Interface`) — no changes needed to the
merge script itself.

```python
#!/usr/bin/env python3
"""
Poll a SonicWall TZ370's ARP cache via SNMP and write it to tz370_arp_cache.csv
in the same column layout as the manual GUI export, so merge-sonicwall-arp.py
doesn't need to change.

Reads the SNMP community string from an environment variable rather than
hardcoding it:

    SNMP_COMMUNITY   the v2c community string configured on the TZ370
    SONICWALL_HOST   optional, defaults to 10.100.126.1

Shells out to `snmpwalk` (Net-SNMP) rather than pulling in pysnmp/easysnmp,
since snmpwalk is already installed and confirmed working on this box.

Columns produced: IP Address, Type, MAC Address, Vendor, Interface
(matches the manual GUI export format exactly, minus the Timeout column,
which has no SNMP equivalent -- see notes below)

Notes / known limitations:
  - "Vendor" is filled in via local OUI lookup (the `manuf` package, same OUI
    source used elsewhere in Discovery) if it's installed; otherwise left blank.
  - Interface names are built directly as "X{ifIndex}" from the ifIndex value
    embedded in each ARP table entry's own OID -- this was empirically
    confirmed against the TZ370's own SNMP output (ifIndex 0-6 map directly
    to X0-X6). An earlier version of this script cross-referenced IF-MIB's
    ifDescr table instead, but that table uses a different index numbering
    on this appliance and produced wrong/offset interface names.
  - There is no SNMP equivalent to the GUI's "Expires in N minutes" column,
    so it's omitted entirely rather than filled with a placeholder, to match
    the working CSV format merge-sonicwall-arp.py expects.
"""

import csv
import os
import re
import subprocess
import sys

HOST = os.environ.get("SONICWALL_HOST", "10.100.126.1")
COMMUNITY = os.environ.get("SNMP_COMMUNITY")
OUTFILE = "tz370_arp_cache.csv"

ARP_TABLE_OID = "1.3.6.1.2.1.4.22"

TYPE_MAP = {"1": "Other", "2": "Invalid", "3": "Dynamic", "4": "Static"}

ARP_LINE_RE = re.compile(
    r"^iso\.3\.6\.1\.2\.1\.4\.22\.1\.(?P<col>\d)\.(?P<ifindex>\d+)\.(?P<ip>\d+\.\d+\.\d+\.\d+)"
    r" = (?:Hex-STRING|STRING|INTEGER): (?P<value>.+)$"
)


def snmpwalk(oid, force_hex=False):
    if not COMMUNITY:
        sys.exit("Missing SNMP_COMMUNITY environment variable")
    cmd = ["snmpwalk", "-v2c", "-c", COMMUNITY]
    if force_hex:
        cmd.append("-Ox")
    cmd += [HOST, oid]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"snmpwalk failed: {result.stderr.strip()}")
    return result.stdout.splitlines()


def hex_to_mac(raw):
    """Convert Net-SNMP's 'AA BB CC DD EE FF' hex string to 'AA:BB:CC:DD:EE:FF'."""
    return ":".join(raw.strip().split())


def get_vendor_lookup():
    """Return a lookup(mac) -> vendor function, using `manuf` if installed."""
    try:
        from manuf import manuf

        parser = manuf.MacParser(update=False)

        def lookup(mac):
            try:
                return parser.get_manuf(mac) or ""
            except Exception:
                return ""

        return lookup
    except ImportError:
        return lambda mac: ""


def get_arp_entries():
    """Return list of dicts: ip, ifindex, mac, type."""
    entries = {}
    for line in snmpwalk(ARP_TABLE_OID, force_hex=True):
        m = ARP_LINE_RE.match(line.strip())
        if not m:
            continue
        key = (m.group("ifindex"), m.group("ip"))
        entries.setdefault(key, {"ip": m.group("ip"), "ifindex": m.group("ifindex")})
        col = m.group("col")
        value = m.group("value")
        if col == "2":
            entries[key]["mac"] = hex_to_mac(value)
        elif col == "4":
            entries[key]["type"] = TYPE_MAP.get(value.strip(), "Unknown")
    return list(entries.values())


def main():
    vendor_lookup = get_vendor_lookup()
    entries = get_arp_entries()

    with open(OUTFILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["IP Address", "Type", "MAC Address", "Vendor", "Interface"])
        for e in sorted(entries, key=lambda x: tuple(int(o) for o in x["ip"].split("."))):
            mac = e.get("mac", "")
            writer.writerow(
                [
                    e["ip"],
                    e.get("type", "Unknown"),
                    mac,
                    vendor_lookup(mac) if mac else "",
                    f"X{e['ifindex']}",
                ]
            )

    print(f"Wrote {len(entries)} entries to {OUTFILE}")


if __name__ == "__main__":
    main()
```

### Debugging notes (worth keeping for future sites)

Two mistakes surfaced while getting this working, both worth watching for on
any similar setup:

1. **Forcing hex output (`-Ox`) on every `snmpwalk` call, not just the MAC
   column.** `-Ox` hex-encodes *all* OCTET STRINGs in the response, including
   human-readable ones — an early version applied it to an interface-name
   lookup too and got back garbage instead of text. Only force hex on OIDs
   you specifically need raw bytes from (here, the MAC address column).

2. **Assuming SNMP index tables line up across MIBs.** An early version
   cross-referenced IF-MIB's `ifDescr` table to resolve friendly interface
   names from `ifIndex`. On this appliance, `ifDescr`'s index numbering
   didn't line up with the `ifIndex` embedded in `ipNetToMediaTable` entries
   — it was off by one zone (e.g. `X4` came back as `X3 (Guest)`). The fix
   was to stop cross-referencing entirely and build the interface name
   directly from the ARP table's own embedded `ifIndex` value
   (`ifIndex 0-6` maps directly to `X0-X6` on this appliance, confirmed by
   comparing raw SNMP output against the GUI). Don't assume index parity
   between MIBs on a given vendor's SNMP agent without checking.

Also worth noting: **CSV column count and naming must exactly match** what
the downstream script expects. An extra `Timeout` column (with no SNMP
equivalent to populate it) caused `merge-sonicwall-arp.py` to silently match
zero rows even though the file parsed fine on its own — there was no error,
just quietly wrong output. When feeding one script's output into another,
diff the header row against a known-working reference file rather than
assuming a superset of columns is harmless.

### Expected merge count

`merge-sonicwall-arp.py` only pulls in ARP entries for zones the switch
fabric can't already see (WAN, DMZ, Guest, Voice, and similar zones that
terminate directly on the firewall). Zones already captured via
`arp.py`/`config-pull.py` against the switches themselves (e.g. LAN,
Surveillance) are correctly skipped here to avoid duplication — a merge
count noticeably lower than the total row count in `tz370_arp_cache.csv` is
expected, not a bug. Confirm by breaking down entries per zone:

```bash
cut -d, -f5 tz370_arp_cache.csv | sort | uniq -c
```

### Wiring it into the daily automation

Credential (SNMP community string) added to the existing credentials file,
`~/.config/discovery/cyberark.env`:

```bash
export cyberARK=the_actual_password
export SNMP_COMMUNITY=the_community_string
```

Added to `~/discovery-weekly.sh`, ahead of the merge step so the CSV exists
before `merge-sonicwall-arp.py` runs:

```bash
#!/bin/bash
set -e

source ~/.config/discovery/cyberark.env
cd /path/to/Discovery
source Discovery/bin/activate

python3 config-pull.py -s jc-4500
python3 config-pull.py -s jcedge
python3 arp.py -s jcedge -c jc-core
python3 snmp_arp_cache.py
python3 merge-sonicwall-arp.py
python3 port-map.py -s jcedge -c jc-core -d 10.100.126.6

deactivate

git add .
git diff --cached --quiet || git commit -m "Discovery run $(date '+%Y-%m-%d %H:%M')"

echo "$(date '+%Y-%m-%d %H:%M') - run completed, exit $?" >> ~/discovery-last-run.txt
```

No changes needed to the cron entry itself — it already runs the wrapper
script daily.
