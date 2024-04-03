"""
References:
https://stackoverflow.com/questions/6545023/how-to-sort-ip-addresses-stored-in-dictionary-in-python/6545090#6545090
https://stackoverflow.com/questions/20944483/python-3-sort-a-dict-by-its-values
https://docs.python.org/3.3/tutorial/datastructures.html

Read the inventory file and create arp.json

Example
device-inventory-gl2

command line (executed from the netmiko-gl\port-maps folder)
python arp.py -s gl2

If using vs code debug, the launch.json file will look like this

{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [

        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": true,
            "args": "-s gl2",
            "justMyCode": true
        }
    ]
}

read a file containing the output of "sh ip arp" and create a sorted list of IP addresses and
IP/Mac Address conbinations.

In this example "sh ip arp vl 250". Save output as arp.txt

Internet  10.53.250.4             3   1060.4b9f.62f8  ARPA   Vlan250
Internet  10.53.250.1             -   0012.00f3.febf  ARPA   Vlan250
Internet  10.53.250.2             0   1060.4b9d.db68  ARPA   Vlan250
Internet  10.53.250.12            0   d8d4.3c2e.4b32  ARPA   Vlan250
Internet  10.53.250.15            0   d8d4.3c2e.4b31  ARPA   Vlan250
Internet  10.53.250.11            0   d8d4.3c2e.4b2f  ARPA   Vlan250
Internet  10.53.250.10            0   d8d4.3c2e.4b30  ARPA   Vlan250

Run the script. Output is a list of correctly sorted list of IPs and MAC Addresses.

Output
10.53.250.1
10.53.250.2
10.53.250.4
10.53.250.10
10.53.250.11
10.53.250.12
10.53.250.15

10.53.250.1 0012.00f3.febf
10.53.250.2 1060.4b9d.db68
10.53.250.4 1060.4b9f.62f8
10.53.250.10 d8d4.3c2e.4b30
10.53.250.11 d8d4.3c2e.4b2f
10.53.250.12 d8d4.3c2e.4b32
10.53.250.15 d8d4.3c2e.4b31

"""

import argparse
import json
import os
import re
import struct
import sys
from socket import inet_aton, inet_ntoa

from icecream import ic

import manuf

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"


def get_current_path():
    current_path = os.getcwd()
    return current_path


def ip2long(ip):
    packed = inet_aton(ip)
    lng = struct.unpack("!L", packed)[0]
    return lng


def long2ip(lng):
    packed = struct.pack("!L", lng)
    ip = inet_ntoa(packed)
    return ip


# imported from cisco-Config-pull


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
parser.add_argument("-s", "--site", help="Site name - ex. HQ")
args = parser.parse_args()
site = args.site

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    dev_inv_file = "device-inventory-" + site + ".csv"

loc = get_current_path() + "/"
# dev_inv_file = loc + dev_inv_file
# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print("{} doesn't exist ".format(dev_inv_file))
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file) as devices_file:
    fabric = devices_file.readlines()

print("-" * (len(dev_inv_file) + 23))
print(f"Reading devices from: {loc}\{dev_inv_file}")
print("-" * (len(dev_inv_file) + 23))
uptime = []
for line in fabric:
    line = line.strip("\n")
    # ipaddr = line.split(",")[0]
    # vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    # username = line.split(",")[3]
    # password = line.split(",")[4]

    # - - - - - - - - Old Code - - - -
    # loc = get_current_path()
    # loc = loc + "\\data\\"
    # arp_file = loc + hostname + "-arp.txt"
    # ic(arp_file)
    # # end import
    # - - - - - - - - Old Code - - - -
    loc = os.getcwd() + "/data/"
    # loc = loc + '/data/'
    arp_file = loc + "JC-core-arp.txt"

    print()
    # create a blank list to accept each line in the file
    data1 = []
    try:
        f = open(arp_file, "r")
    except FileNotFoundError:
        print(f"{arp_file} does not exist")
    else:
        # MAC addresses are expressed differently depending on the manufacture and even model of the device
        # the formats that this script can parse are:
        # 0a:0a:0a:0a:0a:0a, 0a-0a-0a-0a-0a-0a, 0a0a0a.0a0a0a0 and 0a0a0a-0a0a0a
        # this should cover most Cisco and HP devices.
        for line in f:
            device_name_loc = line.find("#")
            if device_name_loc != -1:
                device_name = line[0:device_name_loc]
                device_name = device_name.strip()
            if line.find("0000.0000.0000") == 38:
                continue
            match_PC = re.search(r"([0-9A-F]{2}[-:]){5}([0-9A-F]{2})", line, re.I)
            match_Cisco = re.search(r"([0-9A-F]{4}[.]){2}([0-9A-F]{4})", line, re.I)
            match_HP = re.search(r"([0-9A-F]{6}[-])([0-9A-F]{6})", line, re.I)
            # strip out lines without a mac address
            if match_PC or match_Cisco or match_HP:
                data1.append(line)
        f.close
    # Save the cleaned up arp records
    # If the file has a hostname# at the top save it as
    # hostname-arp.txt, else switch-arp.txt
    try:
        if "device_name" in locals():
            save_device = device_name + "-arp.txt"
            device_file = open(save_device, "w")
        else:
            device_name = "switch"
            save_device = device_name + "-arp.txt"
            device_file = open(save_device, "w")
        for line in data1:
            device_file.write(line)
        device_file.close()
    except FileNotFoundError as fnf_error:
        print(fnf_error)
        sys.exit(0)

    # string length
    i = len(data1) - 1
    d = i + 1
    counter = 0
    sItems = []
    IPs = []
    data = {}
    data2 = {}
    while counter <= i:
        IP = data1[counter]
        # Remove Enter
        IP = IP.strip("\n")
        Mac = IP
        MacAndVlan = IP
        ic(IP)
        Vlan = Mac.find("Vlan")
        Mac = Mac[38 : Vlan - 9].rstrip("")
        MacAndVlan = MacAndVlan[38:70].rstrip("")
        ic(MacAndVlan)
        MacAndVlan = MacAndVlan.replace("ARPA   Vlan", "")
        # MacAndVlan = MacAndVlan.replace('  ARPA   FastEther', '')
        ic(MacAndVlan)
        # Find the space after IP
        AfterIP = IP.find("   ")
        # Remove Characters After IP
        IP = IP[0:AfterIP].rstrip("")
        ic(IP)
        # Remove Internet before IP
        IP = IP.replace("Internet  ", "")
        ic(IP)
        IPs.append(str(IP))
        #   Convert IP to a long so it can be sorted.
        #   See https://stackoverflow.com/questions/6545023/how-to-sort-ip-addresses-stored-in-dictionary-in-python/6545090#6545090
        IP = ip2long(IP)
        # add IP address and MAC to dictionary
        data[IP] = Mac
        data2[IP] = MacAndVlan
        counter = counter + 1
    # Sort IPs
    IPs = sorted(IPs, key=lambda ip: struct.unpack("!L", inet_aton(ip))[0])
    print("Number of IP Addresses: %s " % d)
    for IP in IPs:
        print(IP)

    print()
    print("Number of IP and MAC Addresses: %s " % d)
    # Create an empty dictionary to hold mac-ip pairs. Will be used with macaddr.py to output ip with interface
    Mac_IP = {}
    s = [(k, data[k]) for k in sorted(data)]
    for k, v in s:
        #   Convert IP back to dotted quad notation.
        k = long2ip(k)
        print(k, v)
        Mac_IP[v] = k
        if "1cc1.de43.aeb7" in Mac_IP:
            print("The IP for MACA %s is  %s" % (v, k))
    #    print(Mac_IP)

    print()
    print("Number of IP, MAC and VLAN: %s " % d)

    s = [(k, data2[k]) for k in sorted(data2)]
    for k, v in s:
        k = long2ip(k)
        print(k, v)
    #
    #
    # look up manufacture from MAC
    print()
    #
    p = manuf.MacParser()

    # Print IP, MAC, Manufacture
    print("Number of IP, MAC and Manufacture: %s " % d)
    print()
    s = [(k, data[k]) for k in sorted(data)]
    for k, v in s:
        #   Convert IP back to dotted quad notation.
        k = long2ip(k)
        v = v.split()
        v = v[0]
        manufacture = p.get_manuf(v)

        print(k, v, manufacture)
    # Write the dictionary out as Mac2IP.json so that it can be used in macaddr.py
    mydatafile = hostname + "-Mac2IP.json"
    with open(mydatafile, "w") as f:
        json.dump(Mac_IP, f, indent=4)
