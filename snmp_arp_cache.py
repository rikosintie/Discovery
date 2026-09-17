#!/usr/bin/env python3
"""
Poll a firewall's ARP cache via the standard SNMP ARP MIB and write it to
firewall_arp_cache.csv in the same column layout as the SonicWall's manual
GUI export, so merge-sonicwall-arp.py doesn't need to change. Vendor-agnostic:
confirmed working against both a SonicWall TZ370 and a FortiGate 60D with no
code changes.

Usage:
    python3 snmp_arp_cache.py --host 10.20.30.1
    (or set SONICWALL_HOST instead of passing --host every time - handy for
    the cron wrapper script, since there's no per-run prompt to fill in;
    kept under its original name for backward compatibility even though the
    script itself is no longer SonicWall-only)

Reads the SNMP community string from an environment variable rather than a
CLI argument or a hardcoded value, since a CLI argument would leave it
visible in shell history and `ps` output:

    SNMP_COMMUNITY   the v2c community string configured on the firewall

There is no hardcoded default host - every site's firewall has a different
management IP, so either --host or SONICWALL_HOST must be supplied.

Shells out to `snmpwalk` (Net-SNMP) rather than pulling in pysnmp/easysnmp,
since snmpwalk is already installed and confirmed working on this box.

Columns produced: IP Address, Type, MAC Address, Vendor, Interface
(matches the manual GUI export format exactly, minus the Timeout column,
which has no SNMP equivalent -- see notes below)

Notes / known limitations:
  - "Vendor" is filled in via local OUI lookup (the `manuf` package, same OUI
    source used elsewhere in Discovery) if it's installed; otherwise left blank.
  - "Interface" is always left blank. It's kept as a column only so this CSV
    stays in the format the manual GUI export used, which is what
    merge-sonicwall-arp.py expects -- but no downstream script actually
    reads it. A real value would have to be vendor-specific (interface
    naming schemes like SonicWall's "X0"-"X6" don't generalize), and the
    same information is one click away in the firewall's own GUI anyway,
    so it isn't worth building.
  - There is no SNMP equivalent to the GUI's "Expires in N minutes" column,
    so it's omitted entirely rather than filled with a placeholder, to match
    the working CSV format merge-sonicwall-arp.py expects.
"""

import argparse
import csv
import os
import re
import subprocess
import sys

parser = argparse.ArgumentParser(
    description="Poll a firewall's ARP cache via standard SNMP (any vendor) and write it to a CSV merge-sonicwall-arp.py can read."
)
parser.add_argument(
    "-H",
    "--host",
    default=os.environ.get("SONICWALL_HOST"),
    help="Firewall management IP to poll (or set SONICWALL_HOST) - ex. 10.20.30.1",
)
args = parser.parse_args()

HOST = args.host
COMMUNITY = os.environ.get("SNMP_COMMUNITY")
OUTFILE = "firewall_arp_cache.csv"

ARP_TABLE_OID = "1.3.6.1.2.1.4.22"

TYPE_MAP = {"1": "Other", "2": "Invalid", "3": "Dynamic", "4": "Static"}

ARP_LINE_RE = re.compile(
    r"^iso\.3\.6\.1\.2\.1\.4\.22\.1\.(?P<col>\d)\.(?P<ifindex>\d+)\.(?P<ip>\d+\.\d+\.\d+\.\d+)"
    r" = (?:Hex-STRING|STRING|INTEGER): (?P<value>.+)$"
)


def snmpwalk(oid, force_hex=False):
    if not HOST:
        sys.exit("Missing firewall IP - pass --host or set SONICWALL_HOST")
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
    """Return list of dicts: ip, mac, type."""
    entries = {}
    for line in snmpwalk(ARP_TABLE_OID, force_hex=True):
        m = ARP_LINE_RE.match(line.strip())
        if not m:
            continue
        # ifIndex is part of the OID for every column of a given ARP entry,
        # so it's needed here to group col2 (MAC)/col4 (type) lines together
        # correctly -- it's just never carried into the output row itself.
        key = (m.group("ifindex"), m.group("ip"))
        entries.setdefault(key, {"ip": m.group("ip")})
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
                    "",
                ]
            )

    print(f"Wrote {len(entries)} entries to {OUTFILE}")


if __name__ == "__main__":
    main()
