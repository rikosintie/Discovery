#!/usr/bin/env python
"""
Merge a firewall's ARP cache (from snmp_arp_cache.py) into a core switch's
Mac2IP.json.

A core switch's `-c` Mac2IP.json assumes it has an SVI (and therefore an
ARP entry) for every VLAN. Some sites route a subset of VLANs through a
separate firewall instead, so arp.py (which only reads the core switch's own
"show ip arp") never sees those IPs and port-map.py reports them as
No-Match. The firewall is the actual L3 gateway for those VLANs, so its own
ARP cache has the pairing arp.py can't get from the core switch.

Run AFTER arp.py and BEFORE port-map.py, since arp.py overwrites
<core>-Mac2IP.json from scratch on every run:

    python3 arp.py -s jcedge -c jc-core
    python3 merge-firewall-arp.py -c jc-core
    python3 port-map.py -s jcedge -c jc-core -d 10.100.126.6

Every row in the CSV gets merged in, unconditionally -- port-map.py only
ever looks up Mac2IP.json by MAC, and consumes no "Interface" data itself,
so there's nothing to filter by. For a MAC the core switch's own ARP table
already resolved correctly, the firewall's cache should agree on the same
IP, so overwriting it is a harmless no-op rather than something worth
filtering out.
"""

import argparse
import csv
import json
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge a firewall's ARP cache (from snmp_arp_cache.py) into a core switch's Mac2IP.json."
    )
    parser.add_argument(
        "-c",
        "--core",
        required=True,
        help="Core switch name, matching arp.py's -c value - ex. jc-core. "
        "Determines port-maps/<core>-Mac2IP.json.",
    )
    parser.add_argument(
        "--csv",
        default="firewall_arp_cache.csv",
        help="Firewall ARP CSV to merge in (default: firewall_arp_cache.csv, "
        "written by snmp_arp_cache.py)",
    )
    return parser.parse_args()


def to_cisco_mac(mac: str) -> str:
    """18:C2:41:23:9D:14 -> 18c2.4123.9d14, matching arp.py's key format."""
    hex_only = mac.replace(":", "").lower()
    return f"{hex_only[0:4]}.{hex_only[4:8]}.{hex_only[8:12]}"


def main() -> None:
    args = parse_args()
    mac2ip_file = f"port-maps/{args.core}-Mac2IP.json"

    try:
        with open(mac2ip_file, encoding="utf-8") as f:
            mac_ip = json.load(f)
    except FileNotFoundError:
        sys.exit(f"Missing {mac2ip_file} - run arp.py -c {args.core} first")

    try:
        csv_file = open(args.csv, newline="", encoding="utf-8")
    except FileNotFoundError:
        sys.exit(f"Missing ARP CSV '{args.csv}' - run snmp_arp_cache.py first")

    added = 0
    with csv_file as f:
        for row in csv.DictReader(f):
            mac = to_cisco_mac(row["MAC Address"])
            mac_ip[mac] = row["IP Address"]
            added += 1

    with open(mac2ip_file, "w", encoding="utf-8") as f:
        json.dump(mac_ip, f, indent=4)

    print(f"Merged {added} entries from {args.csv} into {mac2ip_file}")


if __name__ == "__main__":
    main()
