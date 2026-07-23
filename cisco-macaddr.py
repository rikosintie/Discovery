"""
References:
https://stackoverflow.com/questions/6545023/how-to-sort-ip-addresses-stored-in-dictionary-in-python/6545090#6545090
https://stackoverflow.com/questions/20944483/python-3-sort-a-dict-by-its-values
https://docs.python.org/3.3/tutorial/datastructures.html
https://www.quora.com/How-do-I-write-a-dictionary-to-a-file-in-Python
https://www.programiz.com/python-programming/break-continue
https://www.ascii-art-generator.org/

read mac-addr.txt containing the output of
show mac add int g1/0/1 | i Gi
show mac add int g1/0/2 | i Gi
show mac add int g1/0/3 | i Gi
show mac add int g1/0/4 | i Gi

and create a list of Vlan, Mac Address, interface and manufacturer.

test-switch#show mac add int g1/0/1 | i Gi
  10    8434.97a7.708b    DYNAMIC     Gi1/0/1
test-switch#show mac add int g1/0/2 | i Gi
test-switch#show mac add int g1/0/3 | i Gi
  10    0c4d.e9c1.4a0d    DYNAMIC     Gi1/0/3
test-switch#show mac add int g1/0/4 | i Gi

Output
Number Entries: 65

Vlan     MAC Address      Interface
  10    8434.97a7.708b     Gi1/0/1   HewlettP
--------------------------------------------------
  10    0c4d.e9c1.4a0d     Gi1/0/3   Apple
--------------------------------------------------

Uses the Parser library for Wireshark's OUI database from
https://github.com/coolbho3k/manuf to convert the MAC to a manufacture.
The database needs to be updated occasionally using:

curl -fSL -o ~/04_tools/Discovery/manuf \
  https://www.wireshark.org/download/automated/data/manuf


Changelog
March 7, 2018
Added code to read Mac2IP.json and use it as a dictionary of IP to MAC.
Mac2IP.json is created by running arp.py against the output
"show ip arp" or "sh ip arp vlan x" on a core switch
if Mac2IP.json is found in the same directory as macaddr.py it adds the
IP address to the output.
if Mac2IP.json is not found the IP address is not added
Vlan     MAC Address      Interface      IP           Vendor
   20    f8b1.56d2.3c13     Gi1/0/3   10.129.20.70    Dell
 ----------------------------------------------------------------
   20    0011.431b.b291     Gi1/0/16   10.129.20.174    Dell
 ----------------------------------------------------------------

March 24, 2018
Added an MD5 hash function to the list of MAC addresses. This gives a
quick comparison of the before
and after is some cables got swapped but are on the correct vlan.
Added a sorted output of the MAC addresses. If there are differences
before and after you can save the list of MACs and use MELD or Notepad++
(with the compare plugin) to see what is different.

Hash of all the MAC addresses
6449620420f0d67bffd26b65e9a824a4

Sorted list of MAC Addresses
0018.c840.1295
0018.c840.12a8
0027.0dbd.9f6e

April 7, 2018
Added output for PingInfoView (https://nirsoft.net)

PingInfo Data
10.56.238.150 b499.ba01.bc82
10.56.239.240 0026.5535.7b7a

April 30, 2018
Added better error trapping for the json and mac-addr.txt.
Stopped stripping DYNAMIC and STATIC from the input.

May 15, 2018
Fixed a bug in the IP address selection loop. I wasn't clearing IP_Data at the
end of the loop so is an interface didn't have an IP address in the json file
it would use the last IP address.

Clear the IP address in case the next interface has a MAC but no IP address
    IP_Data = ''
"""

import argparse
import concurrent.futures
import contextlib
import hashlib
import json
import os
import re
import socket
import sys

import dns.exception
import dns.resolver
import dns.reversename
import rich.box
from icecream import ic
from rich.console import Console
from rich.table import Table

import manuf

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"


vernum = "1.1"


def version():
    """
    This function prints the version of this program. It doesn't allow
    any argument.
    """
    #    print(AsciiArt)
    print("+----------------------------------------------------------------------+")
    print(
        "| "
        + sys.argv[0]
        + " Version "
        + vernum
        + "                                               |"
    )
    print("| This program is free software; you can redistribute it and/or modify |")
    print("| it in any way you want. If you improve it please send me a copy at   |")
    print("| the email address below.                                             |")
    print("|                                                                      |")
    print("| Author: Michael Hubbard, michael.hubbard999@gmail.com                |")
    print("|         mwhubbard.blogspot.com                                       |")
    print("|         @rikosintie                                                  |")
    print("+----------------------------------------------------------------------+")


def remove_empty_lines(filename):
    if not os.path.isfile(filename):
        print("{} does not exist ".format(filename))
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w") as filehandle:
        lines = filter(lambda x: x.strip(), lines)
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
    "-d",
    "--dns",
    default="",
    help="DNS server IP for reverse lookups - ex. 192.168.10.222",
)
args = parser.parse_args()
site = args.site
core = args.coreswitch
dns_server = args.dns

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    dev_inv_file = "device-inventory-" + site + ".csv"

ic(dev_inv_file)
# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print("{} doesn't exist ".format(dev_inv_file))
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
    # create a blank list to accept each line in the file
    # data1 = []
    # try:
    #     f = open(mac_file, 'r')
    # except FileNotFoundError:
    #             print(f'{mac_file} does not exist')
    # else:
    #     print()

    # MAC addresses are expressed differently depending on the manufacture and even model device
    # the formats that this script can parse are:
    # 0a:0a:0a:0a:0a:0a, 0a-0a-0a-0a-0a-0a, 0a0a0a.0a0a0a0 and 0a0a0a-0a0a0a
    # this should cover most Cisco and HP devices.
    #

    # create an empty dictionary to hold the mac-IP data
    Mac_IP = {}
    IP_Data = ""
    device_name = hostname
    # create an empty list to hold MAC addresses for hashing
    hash_list = []
    # open the json created by arp.py if it exists
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
            Mac_IP = json.load(f)
    except FileNotFoundError as fnf_error:
        print(fnf_error)
        print("IP Addresses will not be included because Mac2IP.json is not available")
        my_json_file = None
    # create a blank list to accept each line in the file
    data = []
    try:
        with open(mac_file, "r") as f:
            for line in f:
                match_PC = re.search(r"([0-9A-F]{2}[-:]){5}([0-9A-F]{2})", line, re.I)
                match_Cisco = re.search(r"([0-9A-F]{4}[.]){2}([0-9A-F]{4})", line, re.I)
                match_HP = re.search(r"([0-9A-F]{6}[-])([0-9A-F]{6})", line, re.I)
                # strip out lines without a mac address
                if match_PC or match_Cisco or match_HP:
                    data.append(line)
                match_prompt = re.match(r"^(\S+?)(?:\([^)]*\))?#", line)
                if match_prompt:
                    device_name = match_prompt.group(1)
                ic(device_name)
    except FileNotFoundError as fnf_error:
        print(fnf_error)
        sys.exit(0)
    print()
    print("Device Name: %s " % device_name)
    print("PingInfo Data")

    # Build the rich table — columns defined once based on whether ARP data is available
    if my_json_file:
        table = Table(
            show_header=True,
            header_style="",
            box=rich.box.HORIZONTALS,
            show_edge=False,
            pad_edge=False,
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
        )
        table.add_column("Vlan", min_width=5)
        table.add_column("MAC Address", min_width=18)
        table.add_column("Interface", min_width=12)
        table.add_column("Vendor", min_width=14)

    for raw_line in data:
        IP = raw_line.strip("\n")
        #   The Nexus line adds an * and spaces to the front of the line
        IP = IP.strip("*    ")
        #   The Nexus line includes additional fields that need to be stripped
        IP = IP.replace("  0         F      F   ", "")
        IP = IP.replace("    ~~~      F    F ", "")
        L = str.split(IP)
        if len(L) < 4:
            continue
        Vlan = L[0]
        Mac = L[1]
        Interface_Num = L[3]
        ic(Mac)
        # The interface isn't in the same location on all switches — search for '/'
        for token in L[3:]:
            if "/" in token:
                Interface_Num = token
                break
        hash_list.append(Mac)
        if Mac in Mac_IP:
            IP_Data = Mac_IP[Mac]
        else:
            IP_Data = "No-Match"
        # print the pinginfo data
        print(IP_Data, Mac)
        # Reverse DNS lookup — only when we have a real IP address
        if my_json_file and IP_Data != "No-Match":
            DNS_Name = reverse_dns(IP_Data, dns_server=dns_server)
        else:
            DNS_Name = ""
        manufacture = str(p.get_manuf(Mac) or "")
        if my_json_file:
            table.add_row(Vlan, IP_Data, Mac, Interface_Num, manufacture, DNS_Name)
        else:
            table.add_row(Vlan, Mac, Interface_Num, manufacture)

    output_file = create_filename("port-maps", "-ports.txt", "Final")
    ic(output_file)

    with open(output_file, "w") as f:
        with contextlib.redirect_stdout(f):
            version()
            print()
            print(f"Number of Entries: {table.row_count}")
            print()
            print(f"Device Name: {device_name}")
            print()
        file_console = Console(file=f, highlight=False, force_terminal=True, no_color=True)
        file_console.print(table)
    """
    hash the string of all macs. This gives a quick way to compare the
    before and after MACS
    """

    hash_list_str = str(hash_list)
    # convert the string to bytes
    b = hash_list_str.encode()
    hash_object = hashlib.md5(b)
    print()
    print("Hash of all the MAC addresses")
    print(hash_object.hexdigest())
    print()

    """
    print out the MAC Addresses sorted for review.
    This is useful if the patch cables got mixed up during replacement
    """
    print("Sorted list of MAC Addresses")
    # print(hash_list)
    for x in sorted(hash_list):
        print(x)
    print("End of output")
