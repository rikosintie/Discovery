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

A neighbor whose name field is just an identifier in disguise - a bare MAC,
or an identifier restated with wrapper text ("Serial Number: 00104939517A"
for a ShoreTel phone, matching the MAC already given elsewhere in the same
record) - gets the best available real fact instead: platform, then
manufacturer, then an OUI-guessed vendor as a last resort. See
matching_identifier() and resolve_unnamed() - the detector compares the
digits themselves rather than any vendor's wording, so it needs no
per-vendor phrase list to also catch, say, an Avaya or Polycom doing the
same trick with different words.

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
from manuf2 import manuf  # type: ignore[import-untyped]
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

# The four MAC notations CDP/LLDP chassis/port IDs show up in: Cisco dotted
# (aabb.ccdd.eeff), colon/dash (aa:bb:cc:dd:ee:ff), ProCurve's own
# space-separated form (aa bb cc dd ee ff), and bare hex with no separator at
# all - some Cisco Small Business gear (SG500X seen in the wild) reports its
# base MAC as the CDP device-id with nothing configured, e.g. "d4d748d09b00".
_MAC_PATTERNS = (
    re.compile(r"^([0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}$"),
    re.compile(r"^([0-9a-fA-F]{2}[:\-]){5}[0-9a-fA-F]{2}$"),
    re.compile(r"^([0-9a-fA-F]{2} ){5}[0-9a-fA-F]{2}$"),
    re.compile(r"^[0-9a-fA-F]{12}$"),
)

_mac_parser: manuf.MacParser | None = None

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


def is_mac(text: str) -> bool:
    """True if `text` is a MAC in any of the CDP/LLDP notations seen here."""
    return any(pattern.match(text) for pattern in _MAC_PATTERNS)


def matching_identifier(name: str, identifiers) -> str | None:
    """The entry in `identifiers` that `name` is just restating, or None.

    Some devices wrap an identifier in a word or two instead of sending a
    real name - ShoreTel phones give "Serial Number: 00104939517A" where
    neighbor_port_id already has the same MAC as "0010.4939.517a". Rather
    than pattern-match "Serial Number:" (a fix that would only ever cover
    ShoreTel), this checks whether `name` contains that MAC written out in
    any of the notations is_mac() recognizes (bare, colon, dash, dot-grouped,
    space) - vendor agnostic, since it's the digits that have to match, not
    whatever English words or punctuation a particular vendor wrapped around
    them. Works the same way for a hypothetical Avaya "MAC-0010.4939.517A"
    or Polycom "SN 00-10-49-39-51-7A" with no new code; a plain word like
    "Serial" can't false-match, since it requires the full 12 hex digits of
    a real identifier in one recognized grouping, not a handful of
    coincidental hex-looking letters.

    `identifiers` is typically (chassis_id, neighbor_port_id, mac_address)
    from the same record - whichever of those are present.
    """
    name_lower = name.lower()
    for identifier in identifiers:
        bare = re.sub(r"[^0-9a-fA-F]", "", identifier or "")
        if len(bare) != 12:
            continue
        bare = bare.lower()
        notations = (
            bare,
            ":".join(bare[i : i + 2] for i in range(0, 12, 2)),
            "-".join(bare[i : i + 2] for i in range(0, 12, 2)),
            ".".join(bare[i : i + 4] for i in range(0, 12, 4)),
            " ".join(bare[i : i + 2] for i in range(0, 12, 2)),
        )
        if any(notation in name_lower for notation in notations):
            return identifier
    return None


def resolve_unnamed(mac: str, platform: str = "", manufacturer: str = "") -> str:
    """Best available label for a neighbor that gave no real name, only an
    identifier (a bare chassis MAC, or a name that's just an identifier
    restated - see matching_identifier()).

    A neighbor_name field is a courtesy, not a requirement: LLDP (and CDP, in
    practice) only require a Chassis ID, Port ID, and TTL, so plenty of real
    endpoints never send a name (Windows' built-in LLDP responder on a
    NIC/dock is the common case, not a misconfigured switch). But the same
    record often still has other fields worth showing instead, checked in
    order of how likely they are to be useful across vendors - a schema
    field beats guessing from text, so no per-vendor parsing is needed:

      1. platform     - "Cisco SG500X-24 (PID:SG500X-24-K9)-VSD" beats a MAC.
      2. manufacturer  - LLDP's own field for this; populated on some records
                         (a Mitel phone) even when platform/name are blank.
      3. an OUI guess  - looked up the same way port-map.py resolves a Vendor
                         column, via manuf2's bundled database, and suffixed
                         "(unnamed)" rather than shown bare - a bare vendor
                         name would read as if the device advertised it, when
                         really it's a guess from the MAC alone.
    """
    cleaned_platform = strip_vendor_prefix(platform)
    if cleaned_platform:
        return cleaned_platform
    cleaned_manufacturer = strip_vendor_prefix(manufacturer)
    if cleaned_manufacturer:
        return cleaned_manufacturer

    global _mac_parser
    if _mac_parser is None:
        _mac_parser = manuf.MacParser()
    normalized = re.sub(r"[.:\- ]", "", mac)
    try:
        colon_form = ":".join(normalized[i : i + 2] for i in range(0, 12, 2))
        vendor = _mac_parser.get_manuf(colon_form) or "Unknown-OUI"
    except (ValueError, IndexError):
        vendor = "Unknown-OUI"
    return f"{vendor} (unnamed)"


def tidy_name(
    raw: str, platform: str = "", manufacturer: str = "", identifiers=()
) -> str:
    """Trim a neighbor id to something that fits the Name column.

    "JC-Core.tricommanagement.local" -> "JC-Core" (a bare FQDN, so drop the
    domain). "90b1.1c63.485e" (a bare MAC) or "Serial Number: 00104939517A"
    (an identifier restated with wrapper text, per matching_identifier())
    -> resolve_unnamed()'s platform/manufacturer/OUI-guess chain, since
    either case is the "no real name" situation, not a hostname to
    cosmetically trim. Free-text ids with a space, like "regDN
    2148,MINET_6940", are left alone.
    """
    text = (raw or "").strip()
    if is_mac(text):
        return resolve_unnamed(text, platform, manufacturer)
    disguised = matching_identifier(text, identifiers)
    if disguised:
        return resolve_unnamed(disguised, platform, manufacturer)
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
            tidy_name(
                row["name"],
                row["platform"],
                row.get("manufacturer", ""),
                row.get("identifiers", ()),
            ),
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
