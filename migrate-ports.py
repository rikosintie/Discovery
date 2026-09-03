r"""
!!!!! Helper Script - Does not change the running config !!!!!

This is for Cisco IOS to Aruba CX migration.

Reads the Interface/<hostname>-interface.json file created by config-pull.py and
builds a migration config snippet for two kinds of interfaces that are
"up": uplinks (module 1 ports, matched by the [0-8]/1/[0-9]{1,2} pattern —
e.g. Gi1/1/3) and SVIs (VlanN). For each matching interface, writes an
"interface / description / ip address / exit" block to
<hostname>-interface-migrate.txt, for pasting into the replacement switch's
config during a cutover.

This script does not connect to any switch — it only reads a JSON file
already on disk and writes a text file. There is no netmiko/SSH involved.

python migrate-ports.py -s <site name>

References:
https://linuxhandbook.com/python-write-list-file/
https://www.tutorialspoint.com/python3/python_dictionary.htm
"""

# !!!!! Helper Script - Does not change the running config !!!!!

__author__ = "Michael Hubbard"
__author_email__ = "michael.hubbard999@gmail.com"
__author_email__ = "mhubbard@network-dev.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  migrate-ports.py
# Cisco Change Request data collection


import argparse
import json
import os
import re
import sys
from datetime import datetime


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
    with open(filename, encoding="utf-8-sig") as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w", encoding="utf-8") as filehandle:
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


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--site", help="Site name - ex. HQ")
args = parser.parse_args()
site = args.site

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    # Use dashes and lowercase letters, in site names/hostnames — they're
    # reused verbatim to build every downstream filename, and a mismatch
    # fails silently. Lowercase also makes searching for files easier.
    dev_inv_file = "device-inventory-" + site + ".csv"

# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print(f"{dev_inv_file} doesn't exist ")
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file, encoding="utf-8-sig") as devices_file:
    fabric = devices_file.readlines()

print("-" * (len(dev_inv_file) + 23))
print(f"Reading devices from: {dev_inv_file}")
print("-" * (len(dev_inv_file) + 23))

#  Create the interface-disable files
found_cisco_ios = False
for line in fabric:
    line = line.strip("\n")
    vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    if vendor.lower() == "cisco_ios":
        found_cisco_ios = True
        now = datetime.now().astimezone()
        date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        print(f"{date_time} Creating interface file for {hostname}")
        print(f"Configuring {hostname}")
        cfg_file = create_filename("Interface", "-interface.json")
        print()
        with open(cfg_file, "r", encoding="utf-8") as json_file:
            interfaces = json.load(json_file)
        ports = []
        count = 0
        #  Create a regex to match any port with [0-8]/1/[0-9]{1,2}
        #  This will match all ports with a 1 as the module number

        regexpattern = re.compile(r"\w*[0-8]/1/[0-9]{1,2}")
        #  print(f'Regex pattern: {regexpattern}')
        for interface in interfaces:
            a = re.findall(regexpattern, interface["interface"])
            if interface["link_status"] == "up" and len(a):
                count += 1
                iName = interface["interface"]
                iName = iName[-5:]
                iAddress = interface["ip_address"]
                if iAddress == "":
                    IP = ""
                ports.append(
                    "interface "
                    + iName
                    + "\n"
                    + "description "
                    + interface["description"]
                    + "\n"
                    + IP
                    + interface["ip_address"]
                    + "\n"
                    + " exit"
                    + "\n"
                )
        # look for Vlans

        regexpattern = re.compile(r"Vlan[0-9]{1,4}")
        #  print(f'Regex pattern: {regexpattern}')
        for interface in interfaces:
            a = re.findall(regexpattern, interface["interface"])
            if interface["link_status"] == "up" and len(a):
                count += 1
                # Aruba CX uses "vlan 10", not Cisco's "Vlan10" — lowercase,
                # with a space before the number.
                iName = re.sub(r"[Vv]lan(\d+)", r"vlan \1", interface["interface"])
                iAddress = interface["ip_address"]
                IP = "ip address "
                if iAddress == "":
                    IP = ""
                ports.append(
                    "interface "
                    + iName
                    + "\n"
                    + "description "
                    + interface["description"]
                    + "\n"
                    + IP
                    + interface["ip_address"]
                    + "\n"
                    + " exit"
                    + "\n"
                )

        print(f"Number of ports to be migrated on {hostname}: {count}")
        migrate = create_filename("Interface", "-interface-migrate.txt")
        with open(migrate, "w", encoding="utf-8") as file:
            file.writelines(ports)

if not found_cisco_ios:
    print(f"No cisco_ios switch found in {dev_inv_file}")
