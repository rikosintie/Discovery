#!/usr/bin/env python3
"""
interfaces-in-use.py - lists every interface that has ever passed traffic.

Reads the JSON captures config-pull.py writes to Interface/<host>-interface.json
("show interfaces" on HP ProCurve and Cisco IOS/XE, "show interface" on
Aruba AOS-CX) and reports every port with a non-zero traffic counter, plus
the switch's own uptime for context - a switch up a few days with mostly
idle ports probably just has people out; one up for months telling the same
story means those ports are candidates for consolidation.

Replaces procurve-interface-in-use.py, which only understood ProCurve's
schema, and which pointed at "-interface.txt" - a filename config-pull.py
stopped writing when this capture moved to JSON. That script could never
have found a file to read, on any vendor, before this rewrite.

Three schemas, detected from each capture's own keys
-------------------------------------------------------
-interface.json carries no vendor field, so the schema is detected from
which keys are present in the first record:

  * ProCurve      - a literal "total_bytes" counter per port.
  * Cisco IOS/XE  - no byte counter in this command's textfsm output at
                    all; "input_packets"/"output_packets" are the closest
                    equivalent, and are what's checked and shown here.
  * Aruba AOS-CX  - separate rx/tx byte counters, summed to one total to
                    match ProCurve's semantics.

`config-pull.py` runs "show interfaces"/"show interface" for every vendor
above. Two more are collected but can't be read for this purpose:

  * Cisco S300 falls back to "show interfaces status" (its only available
    template), which has no traffic-counter field of any kind - a real
    data limitation, not a bug, so it's reported as such rather than
    guessed at.
  * Cisco NX-OS and ArubaOS-Switch have no matching textfsm template for
    this command in this project as of this writing, so their captures
    are unparsed raw text; that's detected and reported by name too.

Output
------
Unchanged in spirit from procurve-interface-in-use.py: a simple text file
per host, written to CR-data/<host>-Port-data.txt, an uptime line (read
from the same host's own <host>-system.txt, if one exists) followed by one
"Interface <port> - ..." line per port with traffic.

Usage
-----
    python3 interfaces-in-use.py                      # every Interface/*-interface.json
    python3 interfaces-in-use.py -f Interface/2920-interface.json
"""

import argparse
import json
import os
import sys


def discover_captures(one_file: str = "") -> list[str]:
    """Capture files to process: `one_file` if given, else every
    Interface/*-interface.json.
    """
    if one_file:
        return [one_file]
    suffix = "-interface.json"
    try:
        names = os.listdir("Interface")
    except FileNotFoundError:
        return []
    return sorted(
        os.path.join("Interface", name) for name in names if name.endswith(suffix)
    )


def host_from_capture(path: str) -> str:
    """"Interface/2920-interface.json" -> "2920"."""
    return os.path.basename(path)[: -len("-interface.json")]


def load_records(path: str) -> list[dict] | None:
    """Parsed capture, or None if it isn't a JSON list of objects.

    A vendor with no matching textfsm template (cisco_nxos, aruba_osswitch,
    as of this writing) leaves config-pull.py unable to parse the output,
    so it writes the raw CLI text as a JSON string instead of a list - a
    non-list result here means "not parseable", not "no traffic".
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(data, list) or not all(isinstance(rec, dict) for rec in data):
        return None
    return data


def _procurve_ports(records: list[dict]) -> tuple[list[str], int]:
    """ProCurve: "total_bytes" is a real per-port byte counter."""
    lines: list[str] = []
    count = 0
    for rec in records:
        rec = {k.lower(): v for k, v in rec.items()}
        total = rec.get("total_bytes", "0") or "0"
        if total != "0":
            lines.append(f"{rec.get('port', '?')} - total_bytes {total}")
    return lines, len(lines)


def _cisco_ios_ports(records: list[dict]) -> tuple[list[str], int]:
    """Cisco IOS/XE: no byte counter in "show interfaces" - packet counts
    are the closest equivalent.
    """
    lines: list[str] = []
    for rec in records:
        rec = {k.lower(): v for k, v in rec.items()}
        in_pkts = rec.get("input_packets", "0") or "0"
        out_pkts = rec.get("output_packets", "0") or "0"
        if in_pkts == "0" and out_pkts == "0":
            continue
        lines.append(
            f"{rec.get('interface', '?')} - input_packets {in_pkts} "
            f"output_packets {out_pkts}"
        )
    return lines, len(lines)


def _aruba_aoscx_ports(records: list[dict]) -> tuple[list[str], int]:
    """Aruba AOS-CX: separate rx/tx byte counters, summed to one total to
    match ProCurve's "total_bytes" semantics.
    """
    lines: list[str] = []
    for rec in records:
        rec = {k.lower(): v for k, v in rec.items()}
        total = int(rec.get("rx_total_bytes") or 0) + int(rec.get("tx_total_bytes") or 0)
        if total:
            lines.append(f"{rec.get('interface', '?')} - total_bytes {total}")
    return lines, len(lines)


def find_ports_in_use(records: list[dict]) -> tuple[list[str], int] | None:
    """(port lines, count) for ports that have passed traffic - only those,
    not every port - so the two can never drift apart the way "every port
    listed, count printed separately" invites. None if this schema has no
    usable traffic counter: either a recognized platform whose captured
    data just doesn't include one (Cisco S300), or a shape this script
    doesn't otherwise know.
    """
    if not records:
        return [], 0
    keys = {k.lower() for k in records[0]}

    if "total_bytes" in keys and "port" in keys:
        return _procurve_ports(records)
    if "input_packets" in keys and "interface" in keys:
        return _cisco_ios_ports(records)
    if "rx_total_bytes" in keys:
        return _aruba_aoscx_ports(records)
    return None


def uptime_for(host: str) -> str:
    """Best-effort uptime line, read from the same host's own
    <host>-system.txt if one exists and parses - not required, so a
    missing or unparsed file just means no uptime line, not an error.
    """
    path = os.path.join("Interface", f"{host}-system.txt")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return ""
    rec = {k.lower(): v for k, v in data[0].items()}
    if rec.get("uptime"):
        return rec["uptime"]
    # Aruba AOS-CX has no combined uptime string, only separate fields.
    parts = (
        (rec.get("uptime_weeks"), "week"),
        (rec.get("uptime_days"), "day"),
        (rec.get("uptime_hours"), "hour"),
        (rec.get("uptime_minutes"), "minute"),
    )
    return " ".join(
        f"{n} {unit}{'' if n == '1' else 's'}" for n, unit in parts if n and n != "0"
    )


def report_path(host: str) -> str:
    """CR-data/<host>-Port-data.txt, creating the folder if needed."""
    folder = "CR-data"
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{host}-Port-data.txt")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List interfaces that have ever passed traffic."
    )
    parser.add_argument(
        "-f",
        "--file",
        default="",
        help="one capture file instead of every Interface/*-interface.json",
    )
    args = parser.parse_args()

    captures = discover_captures(args.file)
    if not captures:
        target = args.file or "Interface/*-interface.json"
        print(f"No interface captures found ({target}).")
        sys.exit(1)

    for path in captures:
        host = host_from_capture(path)
        records = load_records(path)
        if records is None:
            print(
                f"Skipping {path} - not structured data (no textfsm parser "
                "for this platform's 'show interfaces'/'show interface')."
            )
            continue

        result = find_ports_in_use(records)
        if result is None:
            keys = {k.lower() for k in records[0]} if records else set()
            if "linkstate" in keys:
                print(
                    f"Skipping {path} - this platform's captured data "
                    "('show interfaces status', its only available "
                    "template) has no traffic-counter field."
                )
            else:
                print(f"Skipping {path} - unrecognized interface-data schema.")
            continue
        lines, count = result

        uptime = uptime_for(host)
        out_path = report_path(host)
        with open(out_path, "w", encoding="utf-8") as handle:
            if uptime:
                handle.write(f"\nSystem Uptime: {uptime}\n\n")
            handle.write(f"Number of Interfaces with traffic: {count}\n")
            for line in lines:
                handle.write(f"Interface {line}\n")

        print(f"Writing CR data to {out_path}")
        if uptime:
            print(f"System Uptime: {uptime}")
        print(f"Number of Interfaces with traffic: {count}")
        for line in lines:
            print(f"Hostname: {host} Interface: {line}")


if __name__ == "__main__":
    main()
