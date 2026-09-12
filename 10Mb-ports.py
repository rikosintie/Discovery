#!/usr/bin/env python3
"""
10Mb-ports.py - lists interfaces stuck at 10Mbps, full or half duplex.

Reads the JSON captures config-pull.py writes to Interface/<host>-int_br.txt
("show interfaces brief" on HP ProCurve, "show interfaces status" on Cisco
IOS/XE and Cisco Small Business/S300 gear) and reports every port running
at 10Mb. Smartrate/mGig ports don't support 10Mb, so a port stuck there is
worth finding during discovery, not deployment - it's usually a door access
controller or a building automation controller that will not get replaced
on your timeline. Use the port maps to look up the manufacturer and confirm.

Replaces procurve-10Mb.py, which only understood ProCurve's schema.

Three schemas, detected from each capture's own keys
-----------------------------------------------------
int_br.txt carries no vendor field of its own, so the schema is detected
from which keys are present, not looked up from a device-inventory file:

  * ProCurve      - speed and duplex folded into one field: "mode": "10FDx"
  * Cisco IOS/XE  - separate "speed"/"duplex": "10" or "a-10" (auto-
                    negotiated), "full"/"a-full" etc. "auto"/"auto" means
                    the port never resolved a speed (nothing plugged in),
                    not a 10Mb link.
  * Cisco S300    - also separate fields, but its own vocabulary and
                    capitalization: bare "10", "Full"/"Half"/"--", and a
                    "linkstate" field instead of "status".

config-pull.py also collects this file for cisco_nxos, aruba_aoscx, and
aruba_osswitch, but as of this writing none of the three have a "show
interfaces status" textfsm template anywhere in this project (checked both
the ntc_templates/ folder vendored here and the installed ntc_templates
package) - so their captures are unparsed raw CLI text, not structured
JSON. Rather than guess at a format nobody has ever actually captured here,
that case is detected and reported by name instead of silently skipped or
misparsed.

Output
------
Unchanged from procurve-10Mb.py: one line per 10Mb port, written to
CR-data/<host>-10Mb-Ports.txt.

Usage
-----
    python3 10Mb-ports.py                      # every Interface/*-int_br.txt
    python3 10Mb-ports.py -f Interface/2920-int_br.txt
"""

import argparse
import json
import os
import sys


def discover_captures(one_file: str = "") -> list[str]:
    """Capture files to process: `one_file` if given, else every
    Interface/*-int_br.txt.
    """
    if one_file:
        return [one_file]
    suffix = "-int_br.txt"
    try:
        names = os.listdir("Interface")
    except FileNotFoundError:
        return []
    return sorted(
        os.path.join("Interface", name) for name in names if name.endswith(suffix)
    )


def host_from_capture(path: str) -> str:
    """"Interface/2920-int_br.txt" -> "2920"."""
    return os.path.basename(path)[: -len("-int_br.txt")]


def load_records(path: str) -> list[dict] | None:
    """Parsed capture, or None if it isn't a JSON list of objects.

    A vendor with no "show interfaces status" textfsm template available
    (cisco_nxos, aruba_aoscx, aruba_osswitch, as of this writing) leaves
    config-pull.py unable to parse the output, so it writes the raw CLI
    text as a JSON string instead of a list - a non-list result here means
    "not parseable", not "no 10Mb ports".
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(data, list) or not all(isinstance(rec, dict) for rec in data):
        return None
    return data


_CISCO_DUPLEX_LABEL = {"full": "FDx", "a-full": "FDx", "half": "HDx", "a-half": "HDx"}
_S300_DUPLEX_LABEL = {"full": "FDx", "half": "HDx"}


def _procurve_10mb(records: list[dict]) -> list[str]:
    """ProCurve: speed+duplex folded into one "mode" field, e.g. "10FDx"."""
    found = []
    for rec in records:
        rec = {k.lower(): v for k, v in rec.items()}
        mode = rec.get("mode", "")
        if mode in ("10FDx", "10HDx"):
            found.append(f"{rec.get('port', '?')} - {mode}")
    return found


def _cisco_ios_10mb(records: list[dict]) -> list[str]:
    """Cisco IOS/XE: separate speed/duplex, "10"/"a-10" + "full"/"a-full"."""
    found = []
    for rec in records:
        rec = {k.lower(): v for k, v in rec.items()}
        speed = (rec.get("speed") or "").lower()
        if speed not in ("10", "a-10"):
            continue
        duplex_label = _CISCO_DUPLEX_LABEL.get((rec.get("duplex") or "").lower(), "??x")
        found.append(f"{rec.get('port', '?')} - 10{duplex_label}")
    return found


def _cisco_s300_10mb(records: list[dict]) -> list[str]:
    """Cisco S300: separate SPEED/DUPLEX, bare "10" + "Full"/"Half"/"--"."""
    found = []
    for rec in records:
        rec = {k.lower(): v for k, v in rec.items()}
        if (rec.get("speed") or "").strip() != "10":
            continue
        duplex_label = _S300_DUPLEX_LABEL.get((rec.get("duplex") or "").strip().lower(), "??x")
        found.append(f"{rec.get('port', '?')} - 10{duplex_label}")
    return found


def find_10mb_ports(records: list[dict]) -> list[str]:
    """"<port> - 10FDx"/"10HDx" for every port running 10Mb.

    Picks the schema (ProCurve/Cisco IOS-XE/Cisco S300) from the keys
    present in the first record - see the module docstring.
    """
    if not records:
        return []
    keys = {k.lower() for k in records[0]}

    if "mode" in keys:
        return _procurve_10mb(records)
    if "status" in keys and "duplex" in keys and "speed" in keys:
        return _cisco_ios_10mb(records)
    if "linkstate" in keys and "duplex" in keys and "speed" in keys:
        return _cisco_s300_10mb(records)
    return []


def report_path(host: str) -> str:
    """CR-data/<host>-10Mb-Ports.txt, creating the folder if needed."""
    folder = "CR-data"
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{host}-10Mb-Ports.txt")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List interfaces running at 10Mbps full or half duplex."
    )
    parser.add_argument(
        "-f",
        "--file",
        default="",
        help="one capture file instead of every Interface/*-int_br.txt",
    )
    args = parser.parse_args()

    captures = discover_captures(args.file)
    if not captures:
        target = args.file or "Interface/*-int_br.txt"
        print(f"No interface captures found ({target}).")
        sys.exit(1)

    for path in captures:
        host = host_from_capture(path)
        records = load_records(path)
        if records is None:
            print(
                f"Skipping {path} - not structured data (no textfsm parser "
                "for this platform's 'show interfaces status')."
            )
            continue

        ports = find_10mb_ports(records)
        if not ports:
            print(f"No 10Mbps interfaces found for {host}")
            continue

        out_path = report_path(host)
        with open(out_path, "w", encoding="utf-8") as handle:
            for line in ports:
                handle.write(f"Interface {line}\n")
        print(f"Writing CR data to {out_path}")
        for line in ports:
            print(f"Hostname: {host} Interface: {line}")


if __name__ == "__main__":
    main()
