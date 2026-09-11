#!/usr/bin/env python3
"""
CDP neighbor report - a standalone, port-map.py-styled table of what each
switch sees over CDP.

Reads the JSON captures config-pull.py writes to Interface/<host>-cdp.txt
(Cisco IOS and HP ProCurve; other vendors don't run CDP) and, per host,
prints and writes:

    Name   mgmt_address   Platform   R_Interface   L_Interface   Capabilities   DNS Name

R_Interface is the neighbor's port, L_Interface is the local port. Three
fields are tidied so the table fits a terminal (see ne_common.py):

    platform      "cisco WS-C4500X-16"    -> "WS-C4500X-16"
    capabilities  "Router Switch IGMP"    -> "Ro Sw IGMP"
    interfaces    "GigabitEthernet1/0/13" -> "Gi1/0/13"

The report is also written to Interface/neighbors/<host>-cdp-ne.txt.

Usage
-----
    python3 cdp-ne.py                        # every Interface/*-cdp.txt
    python3 cdp-ne.py -f Interface/jc-mdf-1-cdp.txt
    python3 cdp-ne.py -d 10.100.126.9        # PTR lookups via that server
    python3 cdp-ne.py --no-dns               # skip PTR lookups
"""

import argparse
import sys

import ne_common as nc

KIND = "cdp"
SCRIPT = "cdp-ne.py"


def normalize(rec: dict) -> dict:
    """One CDP record (Cisco or ProCurve) -> the columns the table needs.

    ProCurve has no neighbor_name field - the device id arrives in
    chassis_id (and is a bare MAC when the neighbor sent no id at all).
    """
    name = (rec.get("neighbor_name") or rec.get("chassis_id") or "").strip()
    return {
        "name": name,
        "mgmt": nc.clean_mgmt(rec.get("mgmt_address", "")),
        "platform": nc.strip_vendor_prefix(rec.get("platform", "")),
        "r_interface": nc.shorten_interface(rec.get("neighbor_interface", "")),
        "l_interface": nc.shorten_interface(rec.get("local_interface", "")),
        "caps": nc.abbreviate_cdp_caps(rec.get("capabilities", "")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CDP neighbor report styled like port-map.py."
    )
    parser.add_argument(
        "-f",
        "--file",
        default="",
        help="one capture file instead of every Interface/*-cdp.txt",
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
        target = args.file or "Interface/*-cdp.txt"
        print(f"No CDP captures found ({target}).")
        sys.exit(1)

    screen = nc.stdout_console()

    for path in captures:
        host = nc.host_from_capture(path, KIND)
        records = nc.load_records(path)
        if records is None:
            print(f"Skipping {path} - no CDP data (device not running CDP?).")
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
