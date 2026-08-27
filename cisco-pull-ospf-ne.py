"""
!!!!! Discovery Script - Does not change the running config !!!!!

Pulls routing/neighbor data from Cisco IOS/IOS-XE switches: "show archive
config diff", "show cdp neighbor detail", "show ip eigrp neighbors" and
"show ip ospf neighbor". CDP/EIGRP/OSPF output is parsed with TextFSM and
written as JSON; the config diff is written as raw text.

Usage

1. cisco-pull-ospf-ne.py is included in the Discovery repo. When you clone the
repository it is included.

2. Create a file named device-inventory-<site>.csv.
Example
device-inventory-test.csv

Place the information for each switch in the file. Format is
<IP Address>,cisco_ios,<hostname>,<username>
Example
192.168.10.52,cisco_ios,gl-IDF1,mhubbard

The password is read from the cyberARK environment variable, or pass -p 1
to be prompted for it.

Example:
export cyberARK=your_password

IMPORTANT: use dashes, in <site> and <hostname> — they get
reused verbatim to build every other filename downstream. Mixing "Lab_3850"
and "Lab-3850" produces two different sets of files that never find each
other, and the failure is silent.

3. Execute
python3 cisco-pull-ospf-ne.py -s test

The script reads device-inventory-<site>.csv and sends the show commands.
Output files are written under CR-data/ off the current working directory.

---Error Handling ---
The ConnectHandler call is wrapped in try/except. A connect timeout,
authentication failure or SSH error is trapped, logged to stdout, and the
script moves on to the next device.
"""

# !!!!! Discovery Script - Does not change the running config !!!!!

import argparse
import getpass
import json
import os
import sys
from datetime import datetime

from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)
from paramiko.ssh_exception import SSHException

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"

# # !!!!! Discovery Script - Does not change the running config !!!!!


def create_filename(sub_dir1: str, extension: str = "", sub_dir2: str = "") -> str:
    """
    returns a valid path regardless of the OS

    Args:
        sub_dir1 (str): name of the sub directory off the cwd required
        extension (str): string appended after hostname - ex. -interface.txt
        sub_dir2 (str, optional): if a nested sub_dir is used Defaults to "".

    Returns:
        str: full pathname of the file to be written
    """
    current_path = os.getcwd()
    extension = hostname + extension
    int_report = os.path.join(current_path, sub_dir1, sub_dir2, extension)
    return int_report


def remove_empty_lines(filename):
    if not os.path.isfile(filename):
        print(f"{filename} does not exist ")
        return
    with open(filename, encoding="utf-8-sig") as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w", encoding="utf-8") as filehandle:
        lines = filter(lambda x: x.strip(), lines)
        filehandle.writelines(lines)


def write_json(sub_dir1: str, extension: str, data) -> None:
    """
    Writes TextFSM output to a JSON file under sub_dir1.

    netmiko returns the raw string (not a list) when no TextFSM template
    matches; that is still written so the failure is visible in the file.
    """
    int_report = create_filename(sub_dir1, extension)
    if not isinstance(data, list):
        print(f"  WARNING: no TextFSM match for {os.path.basename(int_report)}")
    print(f"Writing {os.path.basename(int_report)} to {os.path.dirname(int_report)}")
    with open(int_report, "w", encoding="utf-8") as file:
        file.write(json.dumps(data, indent=2))


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--site", help="Site name - ex. MVMS")
parser.add_argument(
    "-p", "--password", default="", help="use -p 1 to be prompted for password"
)
args = parser.parse_args()
site = args.site

if site is None:
    print("-s site name is a required argument")
    sys.exit()

dev_inv_file = "device-inventory-" + site + ".csv"

# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print(f"{dev_inv_file} doesn't exist ")
    sys.exit()

# Check for the password, exit if it doesn't exist
if args.password != "":
    password = getpass.getpass(prompt="Input the Password:")
else:
    password = os.environ.get("cyberARK")

if not password:
    print(
        "No password was found. Either set the environment variable:\n\n"
        "    export cyberARK=your_password\n\n"
        "or pass -p 1 to be prompted:\n\n"
        f"    python3 cisco-pull-ospf-ne.py -s {site} -p 1\n"
    )
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file, encoding="utf-8-sig") as devices_file:
    fabric = devices_file.readlines()

print("-" * (len(dev_inv_file) + 23))
print(f"Reading devices from: {dev_inv_file}")
print("-" * (len(dev_inv_file) + 23))

for line in fabric:
    line = line.strip("\n")
    fields = [field.strip() for field in line.split(",")]
    if len(fields) < 4:
        print(f"Skipping malformed inventory line: {line!r}")
        continue
    ipaddr, vendor, hostname, username = fields[0], fields[1], fields[2], fields[3]

    if vendor.lower() != "cisco_ios":
        continue

    now = datetime.now().astimezone()
    start_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    print("-----------------------------------------------------")
    print(f"{start_time} Connecting to switch {hostname}")
    print("-----------------------------------------------------")
    try:
        device = {
            "device_type": vendor,
            "ip": ipaddr,
            "username": username,
            "password": password,
            "conn_timeout": 60,
        }
        net_connect = ConnectHandler(**device)
    except (
        NetmikoTimeoutException,
        NetmikoAuthenticationException,
        EOFError,
        SSHException,
    ) as error:
        print(f"Could not connect to {hostname}: {error}")
        end_time = datetime.now().astimezone()
        print(f"\nExec time: {end_time - now}\n")
        continue

    try:
        print(f"Processing {hostname}")
        print()
        print(net_connect.find_prompt())

        # pull a config diff
        print(f"processing show archive config diff for {hostname}")
        output_diff = net_connect.send_command(
            "show archive config diff", read_timeout=360
        )

        # Use TextFSM to create a json object with cdp neighbors
        print(f"processing show cdp for {hostname}")
        output_cdp = net_connect.send_command(
            "show cdp neighbor detail", use_textfsm=True
        )

        # Use TextFSM to create a json object with show ip eigrp neighbors
        print(f"processing show eigrp ne for {hostname}")
        output_eigrp_ne = net_connect.send_command(
            "show ip eigrp neighbors", use_textfsm=True
        )

        # Use TextFSM to create a json object with ospf ne
        print(f"processing show IP OSPF NE for {hostname}")
        output_ospf_ne = net_connect.send_command(
            "show ip ospf neighbor", use_textfsm=True
        )
    finally:
        net_connect.disconnect()

    # Write the config diff data to a file
    int_report = create_filename("CR-data", "-diff.txt")
    print(f"Writing config diff data to {int_report}")
    with open(int_report, "w", encoding="utf-8") as file:
        file.write(output_diff)

    # Write the JSON OSPF NE data to a file
    write_json("CR-data", "-ospf_ne.txt", output_ospf_ne)

    # Write the JSON cdp neighbor data to a file
    write_json("CR-data", "-cdp_ne.txt", output_cdp)

    # Write the JSON eigrp neighbor data to a file
    write_json("CR-data", "-eigrp_ne.txt", output_eigrp_ne)

    end_time = datetime.now().astimezone()
    print(f"\nExec time: {end_time - now}\n")
