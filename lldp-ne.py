#!/usr/bin/env python3
"""
LLDP neighbor report - a standalone, port-map.py-styled table of what each
switch sees over LLDP.

Reads the JSON captures config-pull.py writes to Interface/<host>-lldp.txt
(Cisco IOS, HP ProCurve, and most other vendors) and, per host, prints and
writes:

    Name   mgmt_address   Platform   R_Interface   L_Interface   Capabilities   DNS Name

R_Interface is the neighbor's port, L_Interface is the local port. Cisco
reports the neighbor's port in neighbor_port_id (already short, e.g.
"Te1/1"); ProCurve has no such field and uses neighbor_interface. Two
fields are tidied (see ne_common.py):

    platform      "cisco WS-C3850-48U"  -> "WS-C3850-48U"
    interfaces    "GigabitEthernet1/0/1" -> "Gi1/0/1"

LLDP capabilities are already compact - letter flags ("B,T" = bridge,
telephone) or short words - so they are passed through, only collapsing
"bridge, router" to "bridge,router".

The report is also written to Interface/neighbors/<host>-lldp-ne.txt.

Usage
-----
    python3 lldp-ne.py                        # every Interface/*-lldp.txt
    python3 lldp-ne.py -f Interface/jc-mdf-1-lldp.txt
    python3 lldp-ne.py -d 10.100.126.9        # PTR lookups via that server
    python3 lldp-ne.py --no-dns               # skip PTR lookups
"""

import argparse
import sys

import ne_common as nc

KIND = "lldp"
SCRIPT = "lldp-ne.py"


def normalize(rec: dict) -> dict:
    """One LLDP record (Cisco or ProCurve) -> the columns the table needs."""
    name = (rec.get("neighbor_name") or rec.get("chassis_id") or "").strip()
    # Cisco puts the neighbor's port in neighbor_port_id ("Te1/1", or a MAC
    # for a phone); ProCurve has no such field and carries it in
    # neighbor_interface. Fall back the other way for either vendor.
    remote = (
        rec.get("neighbor_port_id")
        or rec.get("neighbor_interface")
        or ""
    ).strip()
    return {
        "name": name,
        "mgmt": nc.clean_mgmt(rec.get("mgmt_address", "")),
        "platform": nc.strip_vendor_prefix(rec.get("platform", "")),
        "r_interface": nc.shorten_interface(remote),
        "l_interface": nc.shorten_interface(rec.get("local_interface", "")),
        "caps": nc.tidy_lldp_caps(rec.get("capabilities", "")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLDP neighbor report styled like port-map.py."
    )
    parser.add_argument(
        "-f",
        "--file",
        default="",
        help="one capture file instead of every Interface/*-lldp.txt",
    )
    parser.add_argument(
        "-d",
        "--dns",
        default="",
        help="DNS server IP for PTR lookups (default: system resolver)",
    )
    parser.add_argument(
        "--no-dns",
        action="store_true",
        help="skip reverse-DNS lookups (leaves the DNS Name column blank)",
    )
    args = parser.parse_args()

    captures = nc.discover_captures(KIND, args.file)
    if not captures:
        target = args.file or "Interface/*-lldp.txt"
        print(f"No LLDP captures found ({target}).")
        sys.exit(1)

    screen = nc.stdout_console()

    for path in captures:
        host = nc.host_from_capture(path, KIND)
        records = nc.load_records(path)
        if records is None:
            print(f"Skipping {path} - no LLDP data (LLDP not enabled?).")
            continue

        table = nc.build_table(
            records, normalize, do_dns=not args.no_dns, dns_server=args.dns
        )
        nc.emit(screen, SCRIPT, host, table)

        out_path = nc.report_path(host, KIND)
        with open(out_path, "w", encoding="utf-8") as handle:
            nc.emit(nc.file_console(handle), SCRIPT, host, table)
        print(f"\nWrote {out_path}\n")


if __name__ == "__main__":
    main()
