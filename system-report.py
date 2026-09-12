#!/usr/bin/env python3
"""
system-report.py - a plain-text system/version summary per switch.

Reads the JSON captures config-pull.py writes to Interface/<host>-system.txt
("show system information" on HP ProCurve; "show version" on Cisco IOS/XE,
NX-OS, and Small Business/S300; "show system" on Aruba AOS-CX) and writes a
labeled key:value report - handy for filling out a Change Request form, and
grep-friendly:

    grep -Eir -b4 "serial number" *system-report.txt

Replaces procurve-system-report.py, which only understood ProCurve's schema.

Five schemas, detected from each capture's own keys
-----------------------------------------------------
-system.txt carries no vendor field, so the schema is detected from which
keys are present in the record:

  * ProCurve      - the richest schema: contact/location, CPU/memory,
                    packet counters, in addition to serial/version/MAC.
  * Cisco IOS/XE  - hostname, uptime (already one combined string), and
                    hardware model/serial/MAC as lists (a stack reports one
                    of each per member).
  * Cisco NX-OS   - hostname, uptime, platform, serial, last reboot reason.
  * Cisco S300    - the sparsest: only software/boot/hardware version - no
                    hostname, serial, or uptime at all.
  * Aruba AOS-CX  - hostname, contact/location, vendor/product, serial, MAC,
                    version, and uptime as separate weeks/days/hours/minutes
                    fields (no combined string, unlike the Cisco platforms).

`config-pull.py` runs "show version"/"show system" for every vendor above.
aruba_osswitch (ArubaOS-Switch) is the one exception - no textfsm template
exists for it anywhere in this project, so its capture is unparsed raw
text. That case is detected and reported by name, not silently skipped.

Output
------
Unchanged in spirit from procurve-system-report.py: a labeled text report
per host, written to Interface/neighbors/<host>-system-report.txt.

Usage
-----
    python3 system-report.py                      # every Interface/*-system.txt
    python3 system-report.py -f Interface/2920-system.txt
"""

import argparse
import json
import os
import sys


def discover_captures(one_file: str = "") -> list[str]:
    """Capture files to process: `one_file` if given, else every
    Interface/*-system.txt.
    """
    if one_file:
        return [one_file]
    suffix = "-system.txt"
    try:
        names = os.listdir("Interface")
    except FileNotFoundError:
        return []
    return sorted(
        os.path.join("Interface", name) for name in names if name.endswith(suffix)
    )


def host_from_capture(path: str) -> str:
    """"Interface/2920-system.txt" -> "2920"."""
    return os.path.basename(path)[: -len("-system.txt")]


def load_record(path: str) -> dict | None:
    """The one system/version record for this host, keys lowercased, or
    None if the capture isn't a JSON list with at least one object in it.

    A vendor with no matching textfsm template (aruba_osswitch, as of this
    writing) leaves config-pull.py unable to parse the output, so it writes
    the raw CLI text as a JSON string instead of a list - a non-list (or
    empty-list) result here means "not parseable", not "nothing to report".
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return None
    return {k.lower(): v for k, v in data[0].items()}


def _join(value) -> str:
    """A textfsm List field (e.g. "hardware": ["WS-C3850-48P"]) -> one
    display string; anything else passes through as plain text.
    """
    if isinstance(value, list):
        return ", ".join(str(v) for v in value if v)
    return str(value or "")


def _procurve_fields(host: str, rec: dict) -> list[tuple[str, str]]:
    return [
        ("Hostname", rec.get("name") or host),
        ("snmp location", rec.get("location", "")),
        ("snmp contact", rec.get("contact", "")),
        ("MAC address age", rec.get("mac_age", "")),
        ("timezone", rec.get("timezone", "")),
        ("daylight_rule", rec.get("daylight_rule", "")),
        ("software_version", rec.get("software_version", "")),
        ("rom_version", rec.get("rom_version", "")),
        ("mac address", rec.get("mac_address", "")),
        ("serial number", rec.get("serial", "")),
        ("system_uptime", rec.get("uptime", "")),
        ("cpu_utilization", rec.get("cpu_util", "")),
        ("mem_free", rec.get("mem_free", "")),
    ]


def _cisco_ios_fields(host: str, rec: dict) -> list[tuple[str, str]]:
    return [
        ("Hostname", rec.get("hostname") or host),
        ("software_version", rec.get("version", "")),
        ("software_image", rec.get("software_image", "")),
        ("hardware", _join(rec.get("hardware"))),
        ("mac address", _join(rec.get("mac_address"))),
        ("serial number", _join(rec.get("serial"))),
        ("system_uptime", rec.get("uptime", "")),
        ("reload_reason", rec.get("reload_reason", "")),
        ("config_register", rec.get("config_register", "")),
    ]


def _cisco_nxos_fields(host: str, rec: dict) -> list[tuple[str, str]]:
    return [
        ("Hostname", rec.get("hostname") or host),
        ("software_version", rec.get("os", "")),
        ("platform", rec.get("platform", "")),
        ("serial number", rec.get("serial", "")),
        ("system_uptime", rec.get("uptime", "")),
        ("last_reboot_reason", rec.get("last_reboot_reason", "")),
        ("boot_image", rec.get("boot_image", "")),
    ]


def _cisco_s300_fields(host: str, rec: dict) -> list[tuple[str, str]]:
    # The sparsest schema this script supports - no hostname, serial, or
    # uptime field exists in "show version" on this platform at all.
    return [
        ("Hostname", host),
        ("software_version", rec.get("sw_version", "")),
        ("boot_version", rec.get("boot_version", "")),
        ("hardware_version", rec.get("hw_version", "")),
    ]


def _aruba_aoscx_fields(host: str, rec: dict) -> list[tuple[str, str]]:
    parts = (
        (rec.get("uptime_weeks"), "week"),
        (rec.get("uptime_days"), "day"),
        (rec.get("uptime_hours"), "hour"),
        (rec.get("uptime_minutes"), "minute"),
    )
    uptime = " ".join(
        f"{n} {unit}{'' if n == '1' else 's'}" for n, unit in parts if n and n != "0"
    )
    return [
        ("Hostname", rec.get("hostname") or host),
        ("snmp location", rec.get("location", "")),
        ("snmp contact", rec.get("contact", "")),
        ("vendor", rec.get("vendor", "")),
        ("product", rec.get("product", "")),
        ("software_version", rec.get("version", "")),
        ("mac address", rec.get("base_mac", "")),
        ("serial number", rec.get("serial", "")),
        ("timezone", rec.get("time_zone", "")),
        ("system_uptime", uptime),
    ]


def build_fields(host: str, rec: dict) -> list[tuple[str, str]] | None:
    """Picks the schema (see module docstring) from the keys present."""
    if "cpu_util" in rec and "mac_age" in rec:
        return _procurve_fields(host, rec)
    if "software_image" in rec:
        return _cisco_ios_fields(host, rec)
    if "last_reboot_reason" in rec:
        return _cisco_nxos_fields(host, rec)
    if "sw_version" in rec and "boot_version" in rec:
        return _cisco_s300_fields(host, rec)
    if "base_mac" in rec:
        return _aruba_aoscx_fields(host, rec)
    return None


def report_path(host: str) -> str:
    """Interface/neighbors/<host>-system-report.txt, creating the folder
    if needed.
    """
    folder = os.path.join("Interface", "neighbors")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{host}-system-report.txt")


def render(fields: list[tuple[str, str]]) -> str:
    """Right-aligned "label: value" lines, one per field."""
    width = max(len(label) for label, _ in fields)
    return "\n".join(f"{label:>{width}}: {value}" for label, value in fields) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write a labeled system/version report per switch."
    )
    parser.add_argument(
        "-f",
        "--file",
        default="",
        help="one capture file instead of every Interface/*-system.txt",
    )
    args = parser.parse_args()

    captures = discover_captures(args.file)
    if not captures:
        target = args.file or "Interface/*-system.txt"
        print(f"No system captures found ({target}).")
        sys.exit(1)

    for path in captures:
        host = host_from_capture(path)
        rec = load_record(path)
        if rec is None:
            print(
                f"Skipping {path} - not structured data (no textfsm parser "
                "for this platform's 'show system'/'show version')."
            )
            continue

        fields = build_fields(host, rec)
        if fields is None:
            print(f"Skipping {path} - unrecognized system-data schema.")
            continue

        text = render(fields)
        out_path = report_path(host)
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Writing system report for {host} to\n {out_path}")
        print(text)


if __name__ == "__main__":
    main()
