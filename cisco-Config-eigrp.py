'''
!!!!!!! Intrusive Script - Use with care !!!!!!!!

Usage
https://pynet.twb-tech.com/blog/netmiko-read-timeout.html
1. Create a new folder and copy cisco-Config-eigrp.py
into it.

2. Create a file named device-inventory-<site>.
Example
device-inventory-test

Place the information for each switch in the file. Format is
<IP Address>,cisco_ios,<hostname>,<username>,<password>
Example
192.168.10.52,cisco_ios,gl-IDF1,mhubbard,7Snb7*BF^8

3. Create a file named <hostname>.txt for each switch and place the
configuration commands for the switch in it.

4. Execute
python3 cisco-Config-eigrp.py -s gl


The script will read the device-inventory-<sitename> file and
execute the contents of the /eigrp/<hostname>.txt for each switch.

For each switch in the inventory file the config commands that were
executed will be saved to /eigrp-data/<hostname>-eigrp_cmd.txt.

Use this file as an audit trail for the configuration commands.

The script will also create a file with a show running configuration
<hostname>-eigrp-running.txt

---Error Handling ---
The connect handler is wrapped in a try/except block.
If a time out occurs when connecting to a switch it is trapped
but the  script halts.
'''

# !!!!!!! Intrusive Script - Use with care !!!!!!!!

from datetime import datetime
from netmiko import ConnectHandler
# from netmiko import exceptions
from paramiko.ssh_exception import SSHException
import os
import argparse
import sys
import json
import logging

# !!!!!!! Intrusive Script - Use with care !!!!!!!!

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"

# uncomment to log all reads and writes on the SSH channel
# logging.basicConfig(filename="test.txt", level=logging.DEBUG) # It will
# logger = logging.getLogger("netmiko")


def remove_empty_lines(filename):
    if not os.path.isfile(filename):
        print("{} does not exist ".format(filename))
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, 'w') as filehandle:
        lines = filter(lambda x: x.strip(), lines)
        filehandle.writelines(lines)


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--site", help="Site name - ex. MVMS")
args = parser.parse_args()
site = args.site

if site is None:
    print('-s site name is a required argument')
    sys.exit()
else:
    dev_inv_file = 'device-inventory-' + site

# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print("{} doesn't exist ".format(dev_inv_file))
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file) as devices_file:
    fabric = devices_file.readlines()

print('-' * (len(dev_inv_file) + 23))
print(f'Reading devices from: {dev_inv_file}')
print('-' * (len(dev_inv_file) + 23))
uptime = []
for line in fabric:
    line = line.strip("\n")
    ipaddr = line.split(",")[0]
    vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    username = line.split(",")[3]
    # password = line.split(",")[4]
    password = os.environ.get('cyberARK')
    if vendor.lower() == "cisco_ios":
        now = datetime.now()
        start_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        print('-----------------------------------------------------')
        print((str(start_time) +
              " Connecting to switch {}".format(hostname)))
        print('-----------------------------------------------------')
        try:
            device = {'device_type': vendor,
                      'ip': ipaddr,
                      'username': username,
                      'password': password,
                      'conn_timeout': 800,

                    }
            net_connect = ConnectHandler(**device)
        except (EOFError, SSHException):
            print(f'Could not connect to {hostname}, remove it'
                  ' from the device inventory file')
            end_time = datetime.now()
            print(f"\nExec time: {end_time - now}\n")
            break
        print(f'Processing {hostname}')

        #  each switch has its config file
        loc = 'D:/Users/Michael.Hubbard/Documents/netmiko-gl/eigrp/'
        cfg_file = loc + hostname + ".txt"
        print()
        print(net_connect.find_prompt())

        # Use textFSM to create a json object with cdp neighbors
        print(f'processing show cdp for {hostname}')
        output_cdp = net_connect.send_command("show cdp neighbor detail",
                                           use_textfsm=True)

        # Use textFSM to create a json object with show ip eigrp neighbors
        print(f'processing show eigrp ne for {hostname}')
        output_eigrp_ne = net_connect.send_command("show ip eigrp neighbors",
                                           use_textfsm=True)

        # Send commands from cfg_file to remove eigrp
        print(f'processing {cfg_file} for {hostname}')
        output_text_eigrp = net_connect.send_config_from_file(cfg_file,
                                                        read_timeout=360)
        output_text_eigrp += net_connect.save_config()        

        #  Write the eigrp commands for auditing output to disk
        loc = 'D:/Users/Michael.Hubbard/Documents/netmiko-gl/eigrp-data/'
        print(f'Writing eigrp data to {loc}{hostname}-eigrp_cmd.txt')
        int_report = loc + hostname + "-eigrp_cmd.txt"
        with open(int_report, 'w') as file:
            file.write(output_text_eigrp)

        # Write the running config to disk
        # print(f'Writing show run to {loc}{hostname}-running-config.txt')
        # int_report = loc + hostname + "-ospf-running.txt"
        # with open(int_report, 'w') as file:
        #     file.write(output_text_ospf)

        print(f'processing show IP OSPF NE for {hostname}')
        # Use textFSM to create a json object with osspf ne
        output = net_connect.send_command("show ip ospf neighbor",
                                         use_textfsm=True)

        # grab show running after eigrp is removed
        loc = 'D:/Users/Michael.Hubbard/Documents/netmiko-gl/Running-eigrp/'
        print(f'Collecting show running-config from {hostname}')
        # print(net_connect.find_prompt())
        output_text = net_connect.send_command("show running", read_timeout=600)

        #  Write the running config to disk
        print(f'Writing show run to {loc}{hostname}-running-config.txt')
        int_report = loc + hostname + "-eigrp-running.txt"
        with open(int_report, 'w') as file:
            file.write(output_text)

        #  Write the JSON OSPF NE data to a file
        loc = 'D:/Users/Michael.Hubbard/Documents/netmiko-gl/eigrp-data/'
        print(f'Writing ospf ne data to {hostname}-ospf_ne.txt')
        int_report = loc + hostname + "-ospf_ne.txt"
        with open(int_report, 'w') as file:
            output = json.dumps(output, indent=2)
            file.write(output)

        # Write the JSON cdp neighbor data to a file
        loc = 'D:/Users/Michael.Hubbard/Documents/netmiko-gl/eigrp-data/'
        print(f'Writing cdp ne data to {loc}{hostname}-cdp_ne.txt')
        int_report = loc + hostname + "-cdp_ne.txt"
        with open(int_report, 'w') as file:
            output_cdp = json.dumps(output_cdp, indent=2)
            file.write(output_cdp)
        print()

        # Write the eigrp neighbor JSON data to a file
        loc = 'D:/Users/Michael.Hubbard/Documents/netmiko-gl/eigrp-data/'
        print(f'Writing eigrp neighbor data to {loc}{hostname}-eigrp_ne.txt')
        int_report = loc + hostname + "-eigrp_ne.txt"
        with open(int_report, 'w') as file:
            output_eigrp_ne = json.dumps(output_eigrp_ne, indent=2)
            file.write(output_eigrp_ne)
        print()
