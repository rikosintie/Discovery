'''
Import a json file of port status created by cisco-Config-Pull.py
Pull out ports G*/1/* as these are the uplinks.
# File name - 01_[hostname]-interface-disable.txt
# read the file and send the commands to disable ports.
create a log file 01_[hostname]-disable-output.txt

See cisco-Config-Pull.py docstring for more information
python interface.py -s <site name>

---Error Handling ---
The connect handler is wrapped in a try/except block.
If a time out occurs when connecting to a switch it is trapped
but the  script halts.

References:
https://linuxhandbook.com/python-write-list-file/
https://www.tutorialspoint.com/python3/python_dictionary.htm
'''

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"

from datetime import datetime
# from netmiko import ConnectHandler
# from netmiko import exceptions
# from paramiko.ssh_exception import SSHException
import os
import argparse
import sys
import json
import re


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

#  Create the interface-disable files
for line in fabric:
    line = line.strip("\n")
    ipaddr = line.split(",")[0]
    vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    username = line.split(",")[3]
    password = line.split(",")[4]
    loc = 'D:/Users/Michael.Hubbard/Documents/netmiko/Interface/'
    if vendor.lower() == "cisco_ios":
        now = datetime.now()
        date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
        print((str(date_time) +
              " Creating interface file for {}".format(hostname)))
        print(f'Configuring {hostname}')
        cfg_file = loc + hostname + "-interface.txt"
        print()
        with open(cfg_file, 'r') as json_file:
            interfaces = json.load(json_file)
        ports = []
        count = 0
        #  Create a regex to match any port with [0-8]/1/[0-9]{1,2}
        #  This will match all ports with a 1 as the module number

        regexpattern = re.compile(r'\w*[0-8]/1/[0-9]{1,2}')
        #  print(f'Regex pattern: {regexpattern}')
        for interface in interfaces:
            a = re.findall(regexpattern, interface['interface'])
            if interface['link_status'] == 'up' and len(a):
                count += 1
                iName = interface['interface']
                iName = iName[-5:]
                iAddress = interface['ip_address']
                if iAddress == "":
                    IP = ""
                ports.append('interface ' + iName \
                             + '\n' + 'description ' + interface['description'] + '\n' + \
                             IP + interface['ip_address'] + '\n' + ' exit' + '\n')
# look for Vlans

        regexpattern = re.compile(r'Vlan[0-9]{1,4}')
        #  print(f'Regex pattern: {regexpattern}')
        for interface in interfaces:
            a = re.findall(regexpattern, interface['interface'])
            if interface['link_status'] == 'up' and len(a):
                count += 1
                iName = interface['interface']
                iAddress = interface['ip_address']
                IP = 'ip address '
                if iAddress == "":
                    IP = ""
                ports.append('interface ' + iName \
                             + '\n' + 'description ' + interface['description'] + '\n' + \
                             IP + interface['ip_address'] + '\n' + ' exit' + '\n')                
        
        print(f'Number of ports to be migrated on {hostname}: {count}')
        migrate = loc + hostname + '-interface-migrate.txt'
        with open(migrate, 'w') as file:
            for port in ports:
                file.write(port)


