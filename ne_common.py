"""
Shared helpers for cdp-ne.py and lldp-ne.py, the CDP / LLDP neighbor
reports.

Both scripts read the JSON captures config-pull.py writes to Interface/
(<host>-cdp.txt, <host>-lldp.txt), so there is no raw-CLI parsing here. The
work is normalizing four slightly different record shapes - Cisco IOS vs HP
ProCurve, CDP vs LLDP - into one table, and tidying three noisy fields so
the table fits an 80-column terminal:

  * platform      "cisco WS-C4500X-16"    -> "WS-C4500X-16"
  * capabilities  "Router Switch IGMP"    -> "Ro Sw IGMP"
  * interfaces    "TenGigabitEthernet1/1" -> "Te1/1"

Each caller supplies its own record->dict normalizer, because the
remote-port field differs by protocol; everything else lives here.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import socket
import sys

import dns.exception
import dns.resolver
import dns.reversename
import rich.box
from rich.console import Console
from rich.table import Table

# On Windows, redirecting stdout to a file makes Python fall back to the
# legacy console codepage, which can't encode the box-drawing characters
# rich prints. Force UTF-8 so redirected output matches the terminal - same
# guard port-map.py uses.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERNUM = "1.0"

# The report is meant to be saved and read back later, so it renders at a
# fixed width instead of floating with the terminal - that also keeps the
# piped/redirected output identical to what you see on screen.
CONSOLE_WIDTH = 130

_MAC_WITH_SPACES = re.compile(r"^([0-9a-fA-F]{2} ){5}[0-9a-fA-F]{2}$")

# Cisco long interface names -> the abbreviation the CLI itself accepts and
# that "show mac address-table" already prints, so a neighbor report lines
# up with a port map. Checked longest-prefix-first.
_INTERFACE_PREFIXES: tuple[tuple[str, str], ...] = (
    ("TwentyFiveGigE", "Twe"),
    ("TenGigabitEthernet", "Te"),
    ("TenGigE", "Te"),
    ("FortyGigabitEthernet", "Fo"),
    ("FortyGigE", "Fo"),
    ("HundredGigE", "Hu"),
    ("TwoGigabitEthernet", "Tw"),
    ("GigabitEthernet", "Gi"),
    ("FastEthernet", "Fa"),
    ("Bundle-Ether", "BE"),
    ("Port-channel", "Po"),
    ("Management", "Ma"),
    ("Ethernet", "Et"),
)

# CDP capability words -> abbreviations. Only the two long words that push
# the table past a screen width are shortened; "Host", "Phone", "IGMP",
# "Trans Bridge" etc. are left readable. Add entries here if a site turns up
# something wider.
_CDP_CAP_WORDS: dict[str, str] = {
    "Router": "Ro",
    "Switch": "Sw",
}

# Placeholders CDP/LLDP put in the mgmt-address field when there is no address.
_BLANK_MGMT = {"", " ", "unsupported format", "not advertised"}


def shorten_interface(name: str) -> str:
    """Abbreviate a Cisco long-form interface name; pass anything else through.

    "GigabitEthernet1/0/13" -> "Gi1/0/13", "TenGigabitEthernet1/1" -> "Te1/1".
    ProCurve bare port numbers ("2"), LLDP MAC port-ids, and free text
    ("LAN port", "eth0", "< JC-IDF-2 ... >") are returned unchanged.
    """
    text = (name or "").strip()
    for long_prefix, short in _INTERFACE_PREFIXES:
        if text.lower().startswith(long_prefix.lower()):
            rest = text[len(long_prefix):]
            if rest[:1].isdigit():
                return short + rest
    return text


def abbreviate_cdp_caps(caps: str) -> str:
    """"Router Switch IGMP" -> "Ro Sw IGMP". Unknown words are kept as-is."""
    text = (caps or "").strip()
    if not text:
        return ""
    return " ".join(_CDP_CAP_WORDS.get(word, word) for word in text.split())


def tidy_name(raw: str) -> str:
    """Trim a neighbor id to something that fits the Name column.

    "JC-Core.tricommanagement.local" -> "JC-Core" (a bare FQDN, so drop the
    domain), "fc ec da c4 77 0b" -> "fc:ec:da:c4:77:0b" (a chassis MAC with
    no device id). Free-text ids with a space, like "regDN 2148,MINET_6940",
    are left alone.
    """
    text = (raw or "").strip()
    if _MAC_WITH_SPACES.match(text):
        return text.replace(" ", ":").lower()
    # ProCurve's LLDP parse sometimes lands the sysdescr in neighbor_name
    # ("cisco WS-C3850-48U"); drop the vendor word so the column isn't just
    # a worse copy of Platform.
    text = strip_vendor_prefix(text)
    if " " not in text and "." in text and not text.replace(".", "").isdigit():
        return text.split(".")[0]
    return text


def tidy_lldp_caps(caps: str) -> str:
    """Collapse "bridge, router" -> "bridge,router". Letter flags ("B,T") pass through."""
    return ",".join(part.strip() for part in (caps or "").split(",") if part.strip())


def strip_vendor_prefix(platform: str) -> str:
    """"cisco WS-C4500X-16" -> "WS-C4500X-16"; also trims Cisco's trailing padding."""
    text = (platform or "").strip()
    for prefix in ("cisco ", "Cisco "):
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def clean_mgmt(addr: str) -> str:
    """Blank out the non-address placeholders CDP/LLDP leave in the mgmt field."""
    text = (addr or "").strip()
    return "" if text.lower() in _BLANK_MGMT else text


def reverse_dns(ip: str, timeout: float = 1.0, dns_server: str = "") -> str:
    """PTR lookup, name truncated at the first '.', '/'-joined for multiples.

    Returns "No-PTR" when no record exists and "Timeout" past the deadline.
    Copied from port-map.py so the two reports resolve names the same way.
    """
    if not ip:
        return ""

    def _lookup() -> str:
        try:
            if dns_server:
                resolver = dns.resolver.Resolver(configure=False)
                resolver.nameservers = [dns_server]
                resolver.timeout = timeout
                resolver.lifetime = timeout
                answers = resolver.resolve(dns.reversename.from_address(ip), "PTR")
                names = [str(r.target).rstrip(".") for r in answers]
            else:
                host, aliases, _ = socket.gethostbyaddr(ip)
                names = [host] + [a for a in aliases if a != host]
            seen: set[str] = set()
            unique: list[str] = []
            for short in (name.split(".")[0] for name in names):
                if short not in seen:
                    seen.add(short)
                    unique.append(short)
            return "/".join(unique)
        except (
            dns.resolver.NXDOMAIN,
            dns.resolver.NoAnswer,
            dns.exception.DNSException,
            socket.herror,
            socket.gaierror,
        ):
            return "No-PTR"

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        try:
            return executor.submit(_lookup).result(timeout=timeout + 1.0)
        except concurrent.futures.TimeoutError:
            return "Timeout"


def discover_captures(kind: str, one_file: str = "") -> list[str]:
    """Capture files to process: `one_file` if given, else every
    Interface/*-<kind>.txt (the .bak siblings are skipped by the suffix match).
    """
    if one_file:
        return [one_file]
    suffix = f"-{kind}.txt"
    try:
        names = os.listdir("Interface")
    except FileNotFoundError:
        return []
    return sorted(
        os.path.join("Interface", name) for name in names if name.endswith(suffix)
    )


def host_from_capture(path: str, kind: str) -> str:
    """"Interface/jc-mdf-1-cdp.txt" -> "jc-mdf-1"."""
    return os.path.basename(path)[: -len(f"-{kind}.txt")]


def load_records(path: str) -> list[dict] | None:
    """Parsed capture, or None if it is not a JSON list of objects.

    config-pull.py writes a bare JSON string (e.g. "% LLDP is not enabled")
    when the device has nothing to report, so a non-list result is a normal
    "nothing here", not a parse error.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(data, list) or not all(isinstance(rec, dict) for rec in data):
        return None
    return data


def report_path(host: str, kind: str) -> str:
    """Interface/neighbors/<host>-<kind>-ne.txt, creating the folder if needed."""
    folder = os.path.join("Interface", "neighbors")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{host}-{kind}-ne.txt")


def build_table(
    records: list[dict], normalize, do_dns: bool = True, dns_server: str = ""
) -> Table:
    """A port-map.py-styled table of the normalized neighbor rows.

    With do_dns, each neighbor's mgmt_address gets a reverse-DNS lookup for
    the DNS Name column (via dns_server if given, else the system resolver).
    """
    table = Table(
        show_header=True,
        header_style="",
        box=rich.box.HORIZONTALS,
        show_edge=False,
        pad_edge=False,
        show_lines=True,
    )
    table.add_column("Name", min_width=16, max_width=24)
    table.add_column("mgmt_address", min_width=15)
    table.add_column("Platform", min_width=14, max_width=22)
    table.add_column("R_Interface", min_width=11)
    table.add_column("L_Interface", min_width=11)
    table.add_column("Capabilities", min_width=12)
    table.add_column("DNS Name")
    for rec in records:
        row = normalize(rec)
        if do_dns and row["mgmt"]:
            dns_name = reverse_dns(row["mgmt"], dns_server=dns_server)
        else:
            dns_name = ""
        table.add_row(
            tidy_name(row["name"]),
            row["mgmt"],
            row["platform"],
            row["r_interface"],
            row["l_interface"],
            row["caps"],
            dns_name,
        )
    return table


def stdout_console() -> Console:
    """Console for on-screen output, pinned to CONSOLE_WIDTH."""
    return Console(highlight=False, width=CONSOLE_WIDTH)


def file_console(handle) -> Console:
    """Console that writes a plain-text copy of the report to an open file."""
    return Console(
        file=handle,
        highlight=False,
        force_terminal=True,
        no_color=True,
        width=CONSOLE_WIDTH,
    )


def version_banner(console: Console, script: str) -> None:
    """The port-map.py version box, rendered through the caller's Console."""
    version_line = f"| {script} Version {VERNUM}"
    version_line += " " * max(1, 69 - len(version_line)) + "|"
    for line in (
        "+----------------------------------------------------------------------+",
        version_line,
        "| This program is free software; you can redistribute it and/or modify |",
        "| it in any way you want. If you improve it please send me a copy at   |",
        "| the email address below.                                             |",
        "|                                                                      |",
        "|    Author: Michael Hubbard                                           |",
        "|     email: michael.hubbard999@gmail.com                              |",
        "|     email: mhubbard@network-dev.com                                  |",
        "|      Blog: mwhubbard.blogspot.com                                    |",
        "|         X: @rikosintie                                               |",
        "|  linkedin: www.linkedin.com/in/mwhubbard                             |",
        "+----------------------------------------------------------------------+",
    ):
        console.print(line)


def emit(console: Console, script: str, host: str, table: Table) -> None:
    """Write the full report - banner, counts, table - to one Console."""
    version_banner(console, script)
    console.print()
    console.print(f"Number of Entries: {table.row_count}")
    console.print()
    console.print(f"Device Name: {host}")
    console.print()
    console.print(table)
