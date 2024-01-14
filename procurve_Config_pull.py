"""
!!!!! Discovery Script - Does not change the running config !!!!!

Reference
https://pynet.twb-tech.com/blog/netmiko-read-timeout.html
https://stackoverflow.com/questions/9539921/how-do-i-define-a-function-with-optional-arguments


Usage
1. Create a new folder and copy cisco-Config-Push.py
into it.

2. Create a file named device-inventory-<site>.
Example
device-inventory-test

Place the information for each switch in the file. Format is
<IP Address>,cisco_ios,<hostname>,<username>
Example
192.168.10.52,cisco_ios,gl-IDF1,mhubbard
NOTE: the password is saved in user environment variable.

3. Create a file named test-config-file.txt and place the
configuration commands for the switches in it.

4. Execute
python3 cisco-Config-Pull.py -s test


The script will read the device-inventory-<sitename> file and
execute the contents of the <hostname>-config-file.txt for each switch.

For each switch in the inventory file the config commands that were
executed will be saved to 01_<hostname>-config-output.txt.

Use this file as an audit trail for the configuration commands.

The script will also create file with a show running configuration
01_<hostname>-running-config.txt

---Error Handling ---
The connect handler is wrapped in a try/except block.
If a time out occurs when connecting to a switch it is trapped
but the  script halts.
"""

# !!!!! Discovery Script - Does not change the running config !!!!!
import argparse
import getpass
import json
import logging
import os
import re
import sys
import timeit
from datetime import datetime

from icecream import ic
from netmiko import ConnectHandler
from netmiko.exceptions import AuthenticationException, NetmikoTimeoutException
from paramiko.ssh_exception import SSHException

# !!!!! Discovery Script - Does not change the running config !!!!!

__author__ = "Michael Hubbard"
__author_email__ = "michael.hubbard999@gmail.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  cisco_Config_Pull.py
#  Procurve Change Request data collection
#  Created by Michael Hubbard on 2023-12-20.

# comment out ic.disable() and uncomment ic.enable() to use icecream
ic.enable()
# ic.disable()


def get_current_path(sub_dir1: str, extension: str, sub_dir2="") -> str:
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


def remove_empty_lines(filename: str) -> str:
    """
    Removes empty lines from the file

    Args:
        filename (str): file in the cwd to be opened

    Returns:
        Nothing - updated file is written to disk
    """
    if not os.path.isfile(filename):
        print("{} does not exist ".format(filename))
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w") as filehandle:
        lines = filter(lambda x: x.strip(), lines)
        filehandle.writelines(lines)


start = timeit.default_timer()
parser = argparse.ArgumentParser(
    description="-s site, -l 1 create log.txt, -p 1 prompt for password"
)
parser.add_argument("-s", "--site", help="Site name - ex. HQ")
parser.add_argument(
    "-l",
    "--logging",  # Optional (but recommended) long version
    default="",
    help="use -l 1 to enable logging",
)
parser.add_argument(
    "-p",
    "--password",  # Optional (but recommended) long version
    default="",
    help="use -p 1 to be prompted for password",
)
args = parser.parse_args()
site = args.site

# if -l 1 is passed, turn on logging
if args.logging != "":
    #  log all reads and writes on the SSH channel
    logging.basicConfig(filename="log.txt", level=logging.DEBUG)
    logger = logging.getLogger("netmiko")

# Check for the password, exit if it doesn't exist
password = ""
if args.password != "":
    password = getpass.getpass(prompt="Input the Password:")
elif os.environ.get("cyberARK"):
    password = os.environ.get("cyberARK")
else:
    print("\n" * 3)
    print("-" * 87)
    print("No password has been found. Use")
    print()
    print("    python procurve-Config-pull.py -s site -p 1")
    print()
    print(
        "on the terminal to be prompted for a password or set the environment variable cyberARK"
    )
    print("-" * 87)
    print()
    sys.exit()

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    dev_inv_file = "device-inventory-" + site + ".csv"

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
uptime = []
for line in fabric:
    line = line.strip("\n")
    ipaddr = line.split(",")[0]
    vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    username = line.split(",")[3]

    if vendor.lower() == "hp_procurve":
        now = datetime.now()
        start_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        print("-----------------------------------------------------")
        print((str(start_time) + " Connecting to switch {}".format(hostname)))
        print("-----------------------------------------------------")
        try:
            device = {
                "device_type": vendor,
                "ip": ipaddr,
                "username": username,
                "password": password,
                "conn_timeout": 600,
            }
            net_connect = ConnectHandler(**device)

        except NetmikoTimeoutException:
            end_time = datetime.now()
            print(f"\nExec time: {end_time - now}\n")
            print(
                f"Could not connect to {hostname} at {ipaddr}. The connection timed out. Remove it from the device inventory file"
            )
            continue
        except AuthenticationException:
            end_time = datetime.now()
            print(f"\nExec time: {end_time - now}\n")
            print(
                f"Could not connect to {hostname} at {ipaddr}. The Credentials failed.  Remove it from the device inventory file"
            )
            continue
        except (EOFError, SSHException):
            # catch unexpected exceptions
            print(
                f"Could not connect to {hostname} at {ipaddr}, remove it"
                " from the device inventory file"
            )
            end_time = datetime.now()
            print(f"\nExec time: {end_time - now}\n")
            continue
        print(f"Processing {hostname}")
        #  all switches use the same config file
        # for data collection, the first line in the file must be end
        cfg_file = "procurve" + "-config-file.txt"
        print()
        print(net_connect.find_prompt())

        print("-" * (len(cfg_file) + len(hostname) + 16))
        print(f"processing {cfg_file} for {hostname}")
        print("-" * (len(cfg_file) + len(hostname) + 16))
        remove_empty_lines(cfg_file)
        with open(cfg_file) as config_file:
            show_commands = config_file.readlines()

        # Netmiko normally allows 100 seconds for send_command to complete
        # delay_factor=2 would allow 200 seconds.
        output_show_str: str = ""
        for command in show_commands:
            output_show = net_connect.send_command(
                command, strip_command=False, delay_factor=3
            )
            ic(output_show)
            output_show_str = output_show_str + "\n" + "!---" + "\n" + output_show

        # Use textFSM to create a json object with interface stats
        print(f"collecting show interface for {hostname}")
        output = net_connect.send_command("show interfaces", use_textfsm=True)

        # Use textFSM to create a json object of show system
        print(f"collecting show interface for {hostname}")
        output_system = net_connect.send_command("show system", use_textfsm=True)

        # Use textFSM to create a json object with cdp neighbors
        print(f"collecting show cdp for {hostname}")
        output_cdp = net_connect.send_command(
            "show cdp neighbor detail", use_textfsm=True
        )
        # Use textFSM to create a json object with interface stats
        print(f"collecting show interfaces brief for {hostname}")
        output_show_int_br = net_connect.send_command(
            "show interfaces brief", use_textfsm=True
        )

        # Use textFSM to create a json object with show lldp info remote
        print(f"collecting show lldp neighbors for {hostname}")
        output_show_lldp = net_connect.send_command(
            "show lldp info remote detail", use_textfsm=True
        )

        #  Send commands from mac.txt for human readable output
        print(f"collecting show mac address for {hostname}")
        output_text_mac = net_connect.send_config_from_file("mac.txt", read_timeout=200)

        #  Send commands from arp.txt for human readable output
        print(f"collecting show arp for {hostname}")
        output_text_arp = net_connect.send_config_from_file("arp.txt", read_timeout=200)

        # Send show running
        print(f"Collecting show running-config from {hostname}")
        # print(net_connect.find_prompt())
        output_text_run = net_connect.send_command(
            "show running structured", read_timeout=360
        )

        # Disconnect from the switch and start writing data to disk
        net_connect.disconnect()

        #  Write the show commands output to disk
        int_report = get_current_path("CR-data", "-CR-data.txt")
        print(f"Writing show commands to {int_report}")
        with open(int_report, "w") as file:
            file.write(output_show_str)

        # Write the mac-address output to disk
        int_report = get_current_path("port-maps", "-mac-address.txt", "data")
        print(f"Writing MAC addresses to {int_report}")
        with open(int_report, "w") as file:
            file.write(output_text_mac)

        # Write the arp table plain text output to disk
        int_report = get_current_path("port-maps", "-arp.txt", "data")
        print(f"Writing ARP data to {int_report}")
        with open(int_report, "w") as file:
            file.write(output_text_arp)

        #  Write the running config to disk
        print(f"Writing show run to {int_report}")
        int_report = get_current_path("Running", "-running-config.txt")
        with open(int_report, "w") as file:
            file.write(output_text_run)

        #  Write the JSON system data to a file
        int_report = get_current_path("Interface", "-system.txt")
        print(f"Writing interfaces json data to {int_report}")
        with open(int_report, "w") as file:
            output_system = json.dumps(output_system, indent=2)
            file.write(output_system)

        #  Write the JSON interface data to a file
        int_report = get_current_path("Interface", "-interface.txt")
        print(f"Writing interfaces json data to {int_report}")
        with open(int_report, "w") as file:
            output = json.dumps(output, indent=2)
            file.write(output)

        # Write the JSON interface brief data to a file
        int_report = get_current_path("Interface", "-int_br.txt")
        print(f"Writing interfaces brief data to {int_report}")
        with open(int_report, "w") as file:
            output_show_int_br = json.dumps(output_show_int_br, indent=2)
            file.write(output_show_int_br)

        # Write the JSON cdp neighbor data to a file
        int_report = get_current_path("Interface", "-cdp.txt")
        print(f"Writing cdp neighbor data to {int_report}")
        with open(int_report, "w") as file:
            output_cdp = json.dumps(output_cdp, indent=2)
            file.write(output_cdp)

        # Write the show lldp JSON data to a file
        int_report = get_current_path("Interface", "-lldp.txt")
        print(f"Writing show lldp data to {int_report}")
        with open(int_report, "w") as file:
            output_show_lldp = json.dumps(output_show_lldp, indent=2)
            file.write(output_show_lldp)
        print()

        ports = []
        count = 0
        #  Create a regex to match any port with [0-8]/0/[0-9]{1,2}
        #  This will match all ports with a 0 as the module number
        regexpattern = re.compile(r"G*[0-8]/0/[0-9]{1,2}")

        # count number of interfaces - cisco only
        # interfaces = json.loads(output)
        # for interface in interfaces:
        #     a = re.findall(regexpattern, interface["interface"])
        #     if interface["input_packets"] != "0" and len(a):
        #         # if len(a):
        #         count += 1
    # Cisco only
    # switch_uptime = json.loads(output_ver)
    # # Write the uptime data to a file
    # int_report = get_current_path("CR-data", "-uptime.txt")
    # print(f"Writing uptime to {int_report}")
    # up = "Switch Uptime: " + switch_uptime[0]["uptime"]
    # restart = "Restart Reason: " + switch_uptime[0]["reload_reason"]
    # count = "Gigabit Ports without traffic: " + str(count)
    # details = [up, restart, count]
    # with open(int_report, "w") as file:
    #     for item in details:
    #         file.write("%s\n" % item)
    print("-" * (len(hostname) + 39))
    print(f"Successfully created config files for {hostname}")
    print("-" * (len(hostname) + 39))
stop = timeit.default_timer()
total_time = stop - start
# output running time in a nice format.
mins, secs = divmod(total_time, 60)
hours, mins = divmod(mins, 60)
print(f"Total running time: {hours} Hours {mins} Minutes {round(secs,2)} Seconds\n")
