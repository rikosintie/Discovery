r"""
# !!!!! Helper Script - Does not change the running config !!!!!
References:
https://stackoverflow.com/questions/6545023/how-to-sort-ip-addresses-stored-in-dictionary-in-python/6545090#6545090
https://stackoverflow.com/questions/20944483/python-3-sort-a-dict-by-its-values
https://docs.python.org/3.3/tutorial/datastructures.html

Reads the raw "show ip arp" / "show arp" output (see the *-arp.txt files
config-pull.py's arp collection produces in hte port-maps directory) and creates
a sorted list of IP addresses and IP/MAC combinations, then writes Mac2IP.json
for port-map.py to consume. One script handles all supported vendors: it finds
the IP and MAC on each line by content rather than assuming a fixed column layout, so
it doesn't matter whether the vendor prints "Internet <ip> <age> <mac> ARPA
Vlan" (Cisco) or "<ip> <mac> <type> <port>" (ProCurve).

Example
device-inventory-gl2.csv

command line
python arp.py -s gl2

Cisco example, output of "sh ip arp vl 250", saved as arp.txt:

Internet  10.53.250.4             3   1060.4b9f.62f8  ARPA   Vlan250
Internet  10.53.250.1             -   0012.00f3.febf  ARPA   Vlan250
Internet  10.53.250.2             0   1060.4b9d.db68  ARPA   Vlan250

ProCurve example, output of "show arp":

  IP Address       MAC Address       Type    Port
  192.168.10.142   525400-46e593     dynamic 2

Run the script. Output is a sorted list of IPs and MAC Addresses, plus a
Mac2IP.json file for port-map.py.

Changelog
August 24, 2026
Merged from cisco-arp.py and procurve-arp.py — one script for both vendors.
Replaced cisco-arp.py's fixed-character-offset parsing (fragile — tied to
one exact column layout) with the same content-detection approach used in
port-map.py: find the IP-shaped and MAC-shaped tokens on each line instead
of assuming a fixed position. Also fixed a real bug found along the way:
procurve-arp.py wrote Mac2IP.json to port-maps/data/, but port-map.py only
ever looks in port-maps/ — ProCurve-sourced Core/IDF deployments were
silently never finding their Mac2IP.json.

August 25, 2026
cx-arp.py (Aruba CX) retired too. Its raw "show arp" format — including
real captures with and without a VRF column, echoed prompts, and even one
capture with mixed MAC notations in the same file — turned out to already
parse correctly with zero changes, since the content-detection approach
never assumed a fixed column layout in the first place. cx-arp.py's actual
gap wasn't parsing, it was that it never had a -s site/-c coreswitch/
device-inventory CLI at all (hardcoded arp.txt in, hardcoded Mac2IP.json
out) — this script's existing loop covers that for any vendor already.
"""

import argparse
import json
import os
import re
import struct
import sys
from socket import inet_aton, inet_ntoa

from icecream import ic  # type: ignore[import-untyped]
from manuf2 import manuf  # type: ignore[import-untyped]

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "michael.hubbard999@gmail.com"
__author_email__ = "mhubbard@network-dev.com"
__copyright__ = ""
__license__ = "Unlicense"

# MAC addresses are expressed differently depending on the vendor:
# aa:bb:cc:dd:ee:ff or aa-bb-cc-dd-ee-ff (same pattern, either separator —
# the latter is a Windows convention, not one we've seen from a switch),
# aabb.ccdd.eeff (Cisco), aabbcc-ddeeff (HP ProCurve). Three patterns.
MAC_FORMAT_PATTERNS = (
    re.compile(r"([0-9A-F]{2}[-:]){5}([0-9A-F]{2})", re.IGNORECASE),
    re.compile(r"([0-9A-F]{4}[.]){2}([0-9A-F]{4})", re.IGNORECASE),
    re.compile(r"([0-9A-F]{6}[-])([0-9A-F]{6})", re.IGNORECASE),
)
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def line_has_mac(text: str) -> bool:
    """True if text contains a MAC address in any of the known vendor notations."""
    return any(rx.search(text) for rx in MAC_FORMAT_PATTERNS)


def normalize_mac(mac: str) -> str:
    """Strip separators and lowercase, so the same MAC compares equal across notations."""
    return re.sub(r"[.:-]", "", mac).lower()


def extract_ip_and_mac(line: str) -> tuple[str, str] | None:
    """
    Pull an IP and MAC out of an ARP line regardless of vendor column
    layout. Returns None if the line isn't a real ARP entry — no IP, no
    MAC, or an incomplete/all-zero MAC (Cisco prints 0000.0000.0000 for
    unresolved entries).
    """
    ip_match = IP_PATTERN.search(line)
    if not ip_match:
        return None
    mac = None
    for token in line.split():
        if line_has_mac(token):
            mac = token
            break
    if mac is None:
        return None
    if normalize_mac(mac) == "000000000000":
        return None
    return ip_match.group(0), mac


def ip2long(ip: str) -> int:
    """
    Converts a dotted-quad IP address to an integer, so IPs can be sorted
    numerically instead of as strings (which would put 10.1.0.252 before
    10.112.1.3).

    Args:
        ip (str): Dotted-quad IP address, e.g. "10.1.0.252".

    Returns:
        int: The IP address packed into a 32-bit unsigned integer.
    """
    packed = inet_aton(ip)
    return struct.unpack("!L", packed)[0]


def long2ip(lng: int) -> str:
    """
    Converts an integer produced by ip2long() back to dotted-quad notation.

    Args:
        lng (int): A 32-bit unsigned integer, as returned by ip2long().

    Returns:
        str: Dotted-quad IP address, e.g. "10.1.0.252".
    """
    packed = struct.pack("!L", lng)
    return inet_ntoa(packed)


def remove_empty_lines(filename: str) -> None:
    """
    Removes blank lines from a file in place. The device-inventory read
    loop will misparse a blank line as a device, so this needs to run
    before the CSV is read.

    Args:
        filename (str): Path to the file to clean up.

    Returns:
        None — the file is rewritten on disk.
    """
    if not os.path.isfile(filename):
        print(f"{filename} does not exist ")
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w") as filehandle:
        lines = list(filter(lambda x: x.strip(), lines))
        filehandle.writelines(lines)


def create_filename(sub_dir1: str, extension: str = "", sub_dir2: str = "") -> str:
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
    # Some output dirs (e.g. port-maps/data) are gitignored and won't exist
    # on a fresh clone - create the target dir before anything writes to it.
    os.makedirs(os.path.dirname(int_report), exist_ok=True)
    return int_report


parser = argparse.ArgumentParser(
    description="-s site, -c core hostname in a Core/IDF deployment"
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

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    # Use dashes and lowercase letters, in site names/hostnames — they're
    # reused verbatim to build every downstream filename, and a mismatch
    # fails silently. Lowercase also makes searching for files easier.
    dev_inv_file = "device-inventory-" + site + ".csv"

loc = os.getcwd()
if not os.path.isfile(dev_inv_file):
    print(f"{dev_inv_file} doesn't exist ")
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file) as devices_file:
    fabric = devices_file.readlines()

print("-" * (len(loc) + len(dev_inv_file) + 23))
print(f"Reading devices from: {loc}\\{dev_inv_file}")
print("-" * (len(loc) + len(dev_inv_file) + 23))

for line in fabric:
    line = line.strip("\n")
    hostname = line.split(",")[2]
    if core:
        hostname = core

    arp_file = create_filename("port-maps", "-arp.txt", "data")
    ic(arp_file)
    print()

    device_name = hostname
    data1: list[str] = []
    try:
        with open(arp_file, "r") as f:
            for raw_line in f:
                match_prompt = re.match(r"^(\S+?)(?:\([^)]*\))?#", raw_line)
                if match_prompt:
                    device_name = match_prompt.group(1)
                if extract_ip_and_mac(raw_line) is not None:
                    data1.append(raw_line)
    except FileNotFoundError:
        print(f"{arp_file} does not exist")

    # Save the cleaned-up arp records
    save_device = create_filename("port-maps", "-arp.txt")
    with open(save_device, "w") as device_file:
        device_file.writelines(data1)

    IPs: list[str] = []
    data: dict[int, str] = {}
    for entry in data1:
        parsed = extract_ip_and_mac(entry)
        if parsed is None:
            continue
        ip_addr, mac = parsed
        IPs.append(ip_addr)
        data[ip2long(ip_addr)] = mac

    IPs = sorted(IPs, key=ip2long)
    print(f"Number of IP Addresses: {len(IPs)} ")
    for ip_addr in IPs:
        print(ip_addr)

    print()
    print(f"Number of IP and MAC Addresses: {len(data)} ")
    # Dictionary of mac-ip pairs. Used by port-map.py to add IP/DNS columns.
    Mac_IP: dict[str, str] = {}
    for key in sorted(data):
        ip_addr = long2ip(key)
        mac = data[key]
        print(ip_addr, mac)
        Mac_IP[mac] = ip_addr

    print()
    p = manuf.MacParser()
    print(f"Number of IP, MAC and Manufacture: {len(data)} ")
    print()
    for key in sorted(data):
        ip_addr = long2ip(key)
        mac = data[key]
        manufacture = p.get_manuf(mac)
        print(ip_addr, mac, manufacture)

    # Write Mac2IP.json for port-map.py. Same location cisco-arp.py always
    # used (port-maps/, no "data" subdir) — port-map.py only ever looks
    # there, so writing anywhere else means it's silently never found.
    mydatafile = create_filename("port-maps", "-Mac2IP.json")
    with open(mydatafile, "w") as f:
        json.dump(Mac_IP, f, indent=4)
    print(f"Writing {mydatafile}")

    # If this is a Core/IDF deployment, only the core switch has ARP data
    if core:
        break
