"""
!!!!! Discovery Script - Does not change the running config !!!!!

Usage
https://pynet.twb-tech.com/blog/netmiko-read-timeout.html
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
import json
import logging
import os
import re
import sys
from datetime import datetime

from netmiko import ConnectHandler

# from netmiko import exceptions
from paramiko.ssh_exception import SSHException

# !!!!! Discovery Script - Does not change the running config !!!!!

#  log all reads and writes on the SSH channel
# logging.basicConfig(filename="test.txt", level=logging.DEBUG) # It will
# logger = logging.getLogger("netmiko")

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  cisco-Config-Pull.py
#  DHS Change Request data collection
#  Created by Michael Hubbard on 2023-12-20.


def remove_empty_lines(filename):
    if not os.path.isfile(filename):
        print("{} does not exist ".format(filename))
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w") as filehandle:
        lines = filter(lambda x: x.strip(), lines)
        filehandle.writelines(lines)


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--site", help="Site name - ex. MVMS")
args = parser.parse_args()
site = args.site

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    dev_inv_file = "device-inventory-" + site

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
    # password = line.split(",")[4]
    password = os.environ.get("cyberARK")
    if vendor.lower() == "cisco_ios":
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

        except (EOFError, SSHException):
            print(
                f"Could not connect to {hostname}, remove it"
                " from the device inventory file"
            )
            end_time = datetime.now()
            print(f"\nExec time: {end_time - now}\n")
            break
        print(f"Processing {hostname}")
        #  all switches use the same config file
        #  cfg_file = 'gl' + "-config-file.txt"
        # for data collection, first line must be end
        cfg_file = "gl" + "-config-file.txt"
        print()
        print(net_connect.find_prompt())

        #  Send commands from cfg_file for human readable output
        print(f"processing {cfg_file} for {hostname}")
        output_text = net_connect.send_config_from_file(cfg_file, read_timeout=360)

        print(f"processing show interface for {hostname}")
        # Use textFSM to create a json object with interface stats
        output = net_connect.send_command("show interfaces", use_textfsm=True)

        # Use textFSM to create a json object with cdp neighbors
        print(f"processing show cdp for {hostname}")
        output_cdp = net_connect.send_command(
            "show cdp neighbor detail", use_textfsm=True
        )

        # Use textFSM to create a json object with show version
        print(f"processing show version for {hostname}")
        output_ver = net_connect.send_command("show version", use_textfsm=True)

        # Use textFSM to create a json object with show ip eigrp neighbors
        print(f"processing show ip eigrp neighbors for {hostname}")
        output_eigrp_ne = net_connect.send_command(
            "show ip eigrp neighbors", use_textfsm=True
        )

        #  print(output_text)  # print the output as plain text on screen

        #  Send commands from mac.txt for human readable output
        print(f"processing show mac address for {hostname}")
        output_text_mac = net_connect.send_config_from_file("mac.txt", read_timeout=200)
        #  Send commands from arp.txt for human readable output
        print(f"processing show arp for {hostname}")
        output_text_arp = net_connect.send_config_from_file("arp.txt", read_timeout=200)

        # Send show running
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/Running/"
        print(f"Collecting show running-config from {hostname}")
        # print(net_connect.find_prompt())
        output_text_run = net_connect.send_command("show running", read_timeout=360)

        # Disconnect from the switch and start writing data to disk
        net_connect.disconnect()

        #  Write the plain text output to disk
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/CR-data/"
        print(f"Writing CR data to {loc}{hostname}-CR-data.txt")
        int_report = loc + hostname + "-CR-data.txt"
        with open(int_report, "w") as file:
            file.write(output_text)

        # Write the mac-address plain text output to disk
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/port-maps/data/"
        print(f"Writing MAC addresses to {loc}{hostname}-mac-addrss.txt")
        int_report = loc + hostname + "-mac-address.txt"
        with open(int_report, "w") as file:
            file.write(output_text_mac)

        # Write the arp table plain text output to disk
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/port-maps/data/"
        print(f"Writing ARP data to {loc}{hostname}-arp.txt")
        int_report = loc + hostname + "-arp.txt"
        with open(int_report, "w") as file:
            file.write(output_text_arp)

        #  Write the running config to disk
        print(f"Writing show run to {loc}{hostname}-running-config.txt")
        int_report = loc + hostname + "-running-config.txt"
        with open(int_report, "w") as file:
            file.write(output_text_run)

        #  Write the JSON interface data to a file
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/Interface/"
        print(f"Writing interface data to {hostname}-interface.txt")
        int_report = loc + hostname + "-interface.txt"
        with open(int_report, "w") as file:
            output = json.dumps(output, indent=2)
            file.write(output)

        # Write the JSON cdp neighbor data to a file
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/Interface/"
        print(f"Writing interface data to {loc}{hostname}-interface.txt")
        int_report = loc + hostname + "-cdp.txt"
        with open(int_report, "w") as file:
            output_cdp = json.dumps(output_cdp, indent=2)
            file.write(output_cdp)
        # print()

        # Write the JSON version data to a file
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/Interface/"
        print(f"Writing version data to {loc}{hostname}-ver.txt")
        int_report = loc + hostname + "-ver.txt"
        with open(int_report, "w") as file:
            output_ver = json.dumps(output_ver, indent=2)
            file.write(output_ver)
        # print()

        # Write the eigrp JSON data to a file
        loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/CR-data/"
        print(f"Writing eigrp data to {loc}{hostname}-eigrp.txt")
        int_report = loc + hostname + "-eigrp_ne.txt"
        with open(int_report, "w") as file:
            output_eigrp_ne = json.dumps(output_eigrp_ne, indent=2)
            file.write(output_eigrp_ne)
        print()
        # close the session to the switch

        ports = []
        count = 0
        #  Create a regex to match any port with [0-8]/0/[0-9]{1,2}
        #  This will match all ports with a 0 as the module number
        regexpattern = re.compile(r"G*[0-8]/0/[0-9]{1,2}")

        # count number of interfaces
        interfaces = json.loads(output)
        for interface in interfaces:
            a = re.findall(regexpattern, interface["interface"])
            if interface["input_packets"] != "0" and len(a):
                # if len(a):
                count += 1

    switch_uptime = json.loads(output_ver)
    # Write the uptime data to a file
    loc = "D:/Users/Michael.Hubbard/Documents/netmiko-gl/CR-data/"
    int_report = loc + hostname + "-uptime.txt"
    print(f"Writing uptime to {loc}{hostname}-CR-data.txt")
    up = "Switch Uptime: " + switch_uptime[0]["uptime"]
    restart = "Restart Reason: " + switch_uptime[0]["reload_reason"]
    count = "Gigabit Ports without traffic: " + str(count)
    details = [up, restart, count]
    with open(int_report, "w") as file:
        for item in details:
            file.write("%s\n" % item)
    print("-" * (len(hostname) + 39))
    print(f"Successfully created config files for {hostname}")
    print("-" * (len(hostname) + 39))
