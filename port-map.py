"""
References:
https://stackoverflow.com/questions/6545023/how-to-sort-ip-addresses-stored-in-dictionary-in-python/6545090#6545090
https://stackoverflow.com/questions/20944483/python-3-sort-a-dict-by-its-values
https://docs.python.org/3.3/tutorial/datastructures.html
https://www.quora.com/How-do-I-write-a-dictionary-to-a-file-in-Python
https://www.programiz.com/python-programming/break-continue
https://www.ascii-art-generator.org/

Reads the raw "show mac address-table" / "show mac-address" output collected
by config-pull.py for the device's vendor — see MAC_COMMAND_MAP in
config-pull.py, and creates a list of Vlan, Mac Address, interface,
Vendor and DNS Name.

One script handles all supported vendors: it detects the MAC
address format and column order per line rather than assuming a fixed layout,
and — for vendors like HP ProCurve that don't repeat the interface on every
row — carries the interface forward from the echoed command or block header.

Cisco example, output of:
show mac add int g1/0/1 | i Gi
show mac add int g1/0/2 | i Gi

show mac add int g1/0/1 | i Gi
  10    8434.97a7.708b    DYNAMIC     Gi1/0/1
test-switch#show mac add int g1/0/2 | i Gi

Output
Number Entries: 65

Vlan     IP Address         MAC Address          Interface      Vendor                       DNS Name
10       192.168.10.222     000c.29b1.6c05       Gi1/0/47       VMware                       NVR
--------------------------------------------------
10       192.168.10.223     000c.29e0.a4db       Gi1/0/47       VMware                       ubuntu-server
--------------------------------------------------

Uses manuf2 (https://pypi.org/project/manuf2/, a maintained fork of
coolbho3k/manuf) to convert the MAC to a manufacturer. The OUI database
ships bundled with the package, so no manual download/path setup is
needed. To refresh it, run python3 port-map.py --update-manuf — only
needed if you're seeing "None" for the Vendor.

Two other outputs get written each run:

- If a Mac2IP.json exists for this host (or for the site's -c coreswitch
  host, in a Core/IDF deployment) — built by arp.py from a "show ip arp" /
  "show arp" capture — each MAC's IP is looked up in it and added to the
  IP Address/DNS Name columns. If it's not found, those two columns are
  left off the table entirely (see the "Mac2IP.json Not Found" warning).
- A PingInfoView (https://nirsoft.net) import file —
  port-maps/pinginfo/<hostname>-pinginfo.txt — pairing each reachable IP
  with its DNS name (or MAC address, if no DNS name resolves), for
  verifying hosts pre/post cutover.

Changelog
Added DNS lookup
Added a -d/--dns argument. When set, each entry's IP is reverse-resolved
(PTR lookup, via the given DNS server) and shown in a DNS Name column
alongside the existing IP/MAC/Vendor data. Truncates each returned name at
the first ".", joins multiple names with "/", and falls back to "No-PTR" or
"Timeout" rather than leaving the column blank on failure.

August 22, 2026
Renamed from cisco-macaddr.py to port-map.py and generalized to replace
procurve-macaddr.py and cx-macaddr.py — one script for all vendors, creating
the port maps this project is named for. Vlan/MAC column order and
interface-column presence differ by vendor; this now detects both instead
of assuming Cisco's layout.
"""

import argparse
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
from icecream import ic  # type: ignore[import-untyped]
from manuf2 import manuf  # type: ignore[import-untyped]
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "michael.hubbard999@gmail.com"
__author_email__ = "mhubbard@network-dev.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  port-map.py
#  Change Request data collection

vernum = "2.0"

# MAC addresses are expressed differently depending on the vendor:
# aa:bb:cc:dd:ee:ff (Aruba CX) or aa-bb-cc-dd-ee-ff (same pattern, either
# separator — the latter is a Windows convention, not one we've seen from a
# switch), aabb.ccdd.eeff (Cisco), aabbcc-ddeeff (HP ProCurve). Three patterns.
MAC_FORMAT_PATTERNS = (
    re.compile(r"([0-9A-F]{2}[-:]){5}([0-9A-F]{2})", re.IGNORECASE),
    re.compile(r"([0-9A-F]{4}[.]){2}([0-9A-F]{4})", re.IGNORECASE),
    re.compile(r"([0-9A-F]{6}[-])([0-9A-F]{6})", re.IGNORECASE),
)


def line_has_mac(text: str) -> bool:
    return any(rx.search(text) for rx in MAC_FORMAT_PATTERNS)


# Locally-administered (U/L bit set) prefixes that are actually a fixed,
# well-known convention rather than genuine per-connection randomization.
# Most hypervisors (VMware, VirtualBox, Hyper-V) use real registered OUIs
# and don't need an entry here — this is only for the few that don't.
KNOWN_LOCAL_PREFIXES = {
    "525400": "QEMU/KVM",  # libvirt's default MAC prefix range
}


def is_locally_administered(mac: str) -> bool:
    """
    True if the MAC's U/L bit (bit 1 of the first octet) is set — meaning
    it's locally administered/randomized rather than a real vendor-assigned
    OUI. Common on modern devices with MAC randomization enabled (phones,
    laptops joining Wi-Fi) and on VMs (e.g. QEMU/libvirt's 52:54:00 range).
    """
    first_octet = int(normalize_mac(mac)[:2], 16)
    return bool(first_octet & 0x02)


def normalize_mac(mac: str) -> str:
    """
    Strip all separators and lowercase, so the same physical MAC compares
    equal regardless of vendor notation (aabb.ccdd.eeff, aabbcc-ddeeff,
    aa:bb:cc:dd:ee:ff). Needed because Mac2IP.json is built from the ARP
    source's own MAC format (e.g. a Cisco core switch), which won't match
    a differently-formatted target device (e.g. an HP ProCurve) without this.
    """
    return re.sub(r"[.:-]", "", mac).lower()


def version(console: Console) -> None:
    """
    Prints the version banner via the given Console rather than the builtin
    print() — a plain print() here would use rich's global default console,
    which caches its terminal/color detection at first use and doesn't
    re-detect it if sys.stdout is later redirected to a file, leaking ANSI
    codes into the saved output.
    """
    #    print(AsciiArt)
    console.print(
        "+----------------------------------------------------------------------+"
    )
    console.print(
        "| "
        + sys.argv[0]
        + " Version "
        + vernum
        + "                                         |"
    )
    console.print(
        "| This program is free software; you can redistribute it and/or modify |"
    )
    console.print(
        "| it in any way you want. If you improve it please send me a copy at   |"
    )
    console.print(
        "| the email address below.                                             |"
    )
    console.print(
        "|                                                                      |"
    )
    console.print(
        "|    Author: Michael Hubbard                                           |"
    )
    console.print(
        "|     email: michael.hubbard999@gmail.com                              |"
    )
    console.print(
        "|     email: mhubbard@network-dev.com                                  |"
    )
    console.print(
        "|      Blog: mwhubbard.blogspot.com                                    |"
    )
    console.print(
        "|         X: @rikosintie                                               |"
    )
    console.print(
        "|  linkedin: www.linkedin.com/in/mwhubbard                             |"
    )
    console.print(
        "+----------------------------------------------------------------------+"
    )


def remove_empty_lines(filename: str) -> None:
    if not os.path.isfile(filename):
        print(f"{filename} does not exist ")
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w") as filehandle:
        lines = list(filter(lambda x: x.strip(), lines))
        filehandle.writelines(lines)


def reverse_dns(ip: str, timeout: float = 1.0, dns_server: str = "") -> str:
    """
    Reverse DNS lookup with a timeout. Returns hostname(s) truncated at the
    first '.', joined with '/' for multiple names. Returns 'No-PTR' when no
    PTR record exists, 'Timeout' when the lookup exceeds the deadline.

    When dns_server is provided, queries that server directly via dnspython
    instead of using the system resolver.
    """

    def _lookup():
        try:
            if dns_server:
                resolver = dns.resolver.Resolver(configure=False)
                resolver.nameservers = [dns_server]
                resolver.timeout = timeout
                resolver.lifetime = timeout
                rev_name = dns.reversename.from_address(ip)
                answers = resolver.resolve(rev_name, "PTR")
                names = [str(r.target).rstrip(".") for r in answers]
            else:
                hostname, aliases, _ = socket.gethostbyaddr(ip)
                names = [hostname] + [a for a in aliases if a != hostname]
            truncated = [n.split(".")[0] for n in names]
            seen: set[str] = set()
            unique = []
            for n in truncated:
                if n not in seen:
                    seen.add(n)
                    unique.append(n)
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
        future = executor.submit(_lookup)
        try:
            return future.result(timeout=timeout + 1.0)
        except concurrent.futures.TimeoutError:
            return "Timeout"


def create_filename(sub_dir1: str, extension: str = "", sub_dir2="") -> str:
    """
    returns a valid path regardless of the OS

    Args:
        sub_dir1 (str): name of the sub directory off the cwd required
        extension (str, optional): string appended after hostname - ex. -interface.txt
        sub_dir2 (str, optional): if a nested sub_dir is used Defaults to "".

    Returns:
        str: full pathname of the file to be written
    """
    current_path = os.getcwd()
    extension = hostname + extension
    int_report = os.path.join(current_path, sub_dir1, sub_dir2, extension)
    return int_report


parser = argparse.ArgumentParser(
    description="-s site, -c core hostname in a Core/IDF deployment, "
    "-d dns server for reverse lookups, --update-manuf to refresh the OUI database"
)
parser.add_argument(
    "-s",
    "--site",
    help="Site name - ex. HQ",
)
parser.add_argument(
    "-c",
    "--coreswitch",  # Optional (but recommended) long version
    default="",
    help="Coreswitch hostname",
)
parser.add_argument(
    "-d",
    "--dns",
    default="",
    help="DNS server IP for reverse lookups - ex. 192.168.10.222",
)
parser.add_argument(
    "--update-manuf",
    action="store_true",
    default=False,
    help="Download the latest Wireshark OUI database (and WFA registry) and exit — "
    "run this if new devices are showing up with no vendor",
)
args = parser.parse_args()

if args.update_manuf:
    print("Updating the manuf OUI database...")
    manuf.MacParser(update=True)
    print("Done.")
    sys.exit()

site = args.site
core = args.coreswitch
dns_server = args.dns

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    # Use dashes, in site names/hostnames — they're reused
    # verbatim to build every downstream filename, and a mismatch fails silently.
    dev_inv_file = "device-inventory-" + site + ".csv"

ic(dev_inv_file)
# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print(f"{dev_inv_file} doesn't exist ")
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file) as devices_file:
    fabric = devices_file.readlines()

print("-" * (len(dev_inv_file) + 23))
print(f"Reading devices from: {dev_inv_file}")
print("-" * (len(dev_inv_file) + 23))
p = manuf.MacParser()
for line in fabric:
    line = line.strip("\n")
    vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    mac_file = create_filename("port-maps", "-mac-address.txt", "data")
    ic(mac_file)

    print()

    # create an empty dictionary to hold the mac-IP data
    Mac_IP = {}
    IP_Data = ""
    device_name = hostname
    # open the json created by arp.py if it exists
    my_json_file: str | None
    if core:
        temp = hostname
        hostname = core
        my_json_file = create_filename("port-maps", "-Mac2IP.json")
        hostname = temp
    else:
        my_json_file = create_filename("port-maps", "-Mac2IP.json")
    # "JC-core-Mac2IP.json"
    # my_json_file = hostname + "-Mac2IP.json"

    try:
        with open(my_json_file) as f:
            # Normalize keys so lookups work regardless of the source
            # switch's MAC notation vs. the target device's own notation.
            Mac_IP = {normalize_mac(k): v for k, v in json.load(f).items()}
    except FileNotFoundError:
        print(
            Panel.fit(
                f"[yellow]{my_json_file}[/yellow] was not found.\n\n"
                f"IP Address and DNS Name columns will be blank for [cyan]{hostname}[/cyan].\n\n"
                "This is usually a hostname mismatch — check that the "
                "[bold]-c coreswitch[/bold] value passed to the arp script matches "
                "the hostname exactly as it appears in the device-inventory csv "
                "(including hyphens/underscores).",
                title="⚠ Mac2IP.json Not Found",
                border_style="yellow",
            )
        )
        my_json_file = None
    # create a blank list to accept each line in the file, paired with
    # whatever interface was last seen in an echoed command/header line
    data: list[tuple[str, str]] = []
    current_interface = ""
    try:
        with open(mac_file, "r") as f:
            for line in f:
                # strip out lines without a mac address
                if line_has_mac(line):
                    data.append((line, current_interface))
                match_prompt = re.match(r"^(\S+?)(?:\([^)]*\))?#", line)
                if match_prompt:
                    device_name = match_prompt.group(1)
                # Some vendors (HP ProCurve) don't repeat the interface on
                # every MAC row — it only appears in the echoed command
                # ("show mac-address 5") or the block header ("Status and
                # Counters - Port Address Table - 5"). Carry it forward so
                # later rows without their own interface token fall back to it.
                mac_cmd = re.search(
                    r"show mac-?add(?:ress)?\s+(\S+)\s*$", line, re.IGNORECASE
                )
                if mac_cmd:
                    current_interface = mac_cmd.group(1)
                table_header = re.search(r"Port Address Table\s*-\s*(\S+)", line)
                if table_header:
                    current_interface = table_header.group(1)
                ic(device_name)
    except FileNotFoundError as fnf_error:
        print(fnf_error)
        sys.exit(0)
    print()
    print(f"Device Name: {device_name} ")
    print("PingInfo Data")

    # Build the rich table — columns defined once based on whether ARP data is available
    if my_json_file:
        table = Table(
            show_header=True,
            header_style="",
            box=rich.box.HORIZONTALS,
            show_edge=False,
            pad_edge=False,
            show_lines=True,
        )
        table.add_column("Vlan", min_width=5)
        table.add_column("IP Address", min_width=16)
        table.add_column("MAC Address", min_width=18)
        table.add_column("Interface", min_width=12)
        table.add_column("Vendor", min_width=14)
        table.add_column("DNS Name")
    else:
        table = Table(
            show_header=True,
            header_style="",
            box=rich.box.HORIZONTALS,
            show_edge=False,
            pad_edge=False,
            show_lines=True,
        )
        table.add_column("Vlan", min_width=5)
        table.add_column("MAC Address", min_width=18)
        table.add_column("Interface", min_width=12)
        table.add_column("Vendor", min_width=14)

    pinginfo: list[str] = []
    for raw_line, ctx_interface in data:
        IP = raw_line.strip("\n")
        #   The Nexus line adds an * and spaces to the front of the line
        IP = IP.strip("*    ")
        #   The Nexus line includes additional fields that need to be stripped
        IP = IP.replace("  0         F      F   ", "")
        IP = IP.replace("    ~~~      F    F ", "")
        L = str.split(IP)
        if len(L) < 2:
            continue
        # Column order differs by vendor: Cisco/Nexus print "VLAN MAC ...",
        # while ProCurve and Aruba CX print "MAC VLAN ...". Detect which of
        # the first two tokens is actually the MAC instead of assuming a
        # fixed position.
        if line_has_mac(L[0]):
            Mac, Vlan = L[0], L[1]
        else:
            Vlan, Mac = L[0], L[1]
        ic(Mac)
        # The interface isn't always in the same column — search all tokens
        # for one that looks like an interface. Fall back to the interface
        # carried forward from the echoed command/header (ProCurve, which
        # doesn't repeat it on every row).
        Interface_Num = ctx_interface
        for token in L:
            if "/" in token:
                Interface_Num = token
                break
        if normalize_mac(Mac) in Mac_IP:
            IP_Data = Mac_IP[normalize_mac(Mac)]
        else:
            IP_Data = "No-Match"
        # print the pinginfo data
        print(IP_Data, Mac)
        # Reverse DNS lookup — only when we have a real IP address
        if my_json_file and IP_Data != "No-Match":
            DNS_Name = reverse_dns(IP_Data, dns_server=dns_server)
        else:
            DNS_Name = ""
        if is_locally_administered(Mac):
            manufacture = KNOWN_LOCAL_PREFIXES.get(normalize_mac(Mac)[:6], "Randomized")
        else:
            manufacture = str(p.get_manuf(Mac) or "")
        if my_json_file:
            table.add_row(Vlan, IP_Data, Mac, Interface_Num, manufacture, DNS_Name)
        else:
            table.add_row(Vlan, Mac, Interface_Num, manufacture)
        # Build pinginfo entry — skip No-Match IPs, use DNS name if available
        if IP_Data != "No-Match":
            dns_valid = DNS_Name and DNS_Name not in ("No-PTR", "Timeout")
            if dns_valid:
                pinginfo.append(f"{IP_Data} {DNS_Name}")
            else:
                pinginfo.append(f"{IP_Data} {Mac}")

    output_file = create_filename("port-maps", "-ports.txt", "Final")
    ic(output_file)

    with open(output_file, "w") as f:
        file_console = Console(
            file=f, highlight=False, force_terminal=True, no_color=True
        )
        version(file_console)
        file_console.print()
        file_console.print(f"Number of Entries: {table.row_count}")
        file_console.print()
        file_console.print(f"Device Name: {device_name}")
        file_console.print()
        file_console.print(table)

    # Write PingInfo file
    pinginfo_file = create_filename("port-maps", "-pinginfo.txt", "pinginfo")
    os.makedirs(os.path.dirname(pinginfo_file), exist_ok=True)
    pinginfo_header = (
        "===========\n"
        "Pinginfo data to import into PingInfoView. PingInfoView is available here:\n\n"
        "https://www.nirsoft.net/utils/multiple_ping_tool.html\n\n"
        "Use PingInfoView to verify hosts pre/post cutover\n"
        "===========\n\n"
        f"Device Name: {device_name}\n\n"
    )
    with open(pinginfo_file, "w") as f:
        f.write(pinginfo_header)
        f.write("\n".join(pinginfo))
        f.write("\n")
    print(f"Writing PingInfo data to\n {pinginfo_file}")

    print("End of output")
