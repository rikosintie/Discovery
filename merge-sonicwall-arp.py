#!/usr/bin/env python
"""
One-off: merges the SonicWall TZ370's ARP cache into jc-core-Mac2IP.json.

jc-core has no SVIs for the VLANs on the SonicWall's X2/X3/X4/X6 interfaces,
so arp.py (which only reads jc-core's own "show ip arp") never sees those
IPs and port-map.py reports them as No-Match. The SonicWall is the actual
L3 gateway for those VLANs, so its ARP cache has the pairing arp.py can't
get from jc-core.

Run AFTER arp.py and BEFORE port-map.py, since arp.py overwrites
jc-core-Mac2IP.json from scratch on every run:

    python3 arp.py -s jcedge -c jc-core
    python3 merge-sonicwall-arp.py
    python3 port-map.py -s jcedge -c jc-core -d 10.100.126.6
"""

import csv
import json

SONICWALL_CSV = "tz370_arp_cache.csv"
MAC2IP_FILE = "port-maps/jc-core-Mac2IP.json"
VLANS_WITHOUT_SVI = {"X2", "X3", "X4", "X6"}


def to_cisco_mac(mac: str) -> str:
    """18:C2:41:23:9D:14 -> 18c2.4123.9d14, matching arp.py's key format."""
    hex_only = mac.replace(":", "").lower()
    return f"{hex_only[0:4]}.{hex_only[4:8]}.{hex_only[8:12]}"


def main() -> None:
    with open(MAC2IP_FILE, encoding="utf-8") as f:
        mac_ip = json.load(f)

    added = 0
    with open(SONICWALL_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Interface"] not in VLANS_WITHOUT_SVI:
                continue
            mac = to_cisco_mac(row["MAC Address"])
            mac_ip[mac] = row["IP Address"]
            added += 1

    with open(MAC2IP_FILE, "w", encoding="utf-8") as f:
        json.dump(mac_ip, f, indent=4)

    print(f"Merged {added} entries from {SONICWALL_CSV} into {MAC2IP_FILE}")


if __name__ == "__main__":
    main()
