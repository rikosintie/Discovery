# !!!!! Helper Script - Run on offline data !!!!!

import argparse
import json
import os
import platform
import sys

from icecream import ic

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"


def get_current_path():
    current_path = os.getcwd()
    return current_path


def remove_empty_lines(filename):
    '''
    #----------- Based on site name, read the inventory file --------
    '''
    if not os.path.isfile(filename):
        print("{} does not exist ".format(filename))
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, 'w') as filehandle:
        lines = filter(lambda x: x.strip(), lines)
        filehandle.writelines(lines)

# def extract_stack_info(json_data):

#     # Extract the stack information

#     hardware = data[0]['hardware']
#     hardware_info = {}

#     for item in hardware:
#         if item not in hardware_info:
#             hardware_info[item] = 1
#         else:
#             hardware_info[item] += 1

#     return hardware_info


def extract_stack_info(json_data):

    # Extract the stack information
    hardware_per_switch = []
    for switch_data in data:
        hardware = switch_data['hardware']
        hardware_per_switch.extend(hardware)
    return hardware_per_switch


def extract_Interface_speed(json_data):
    '''
    extract_Interface_speed find interfaces with 10Mbps speed

    Arguments:
        json_data -- json data from 'show interfaces, textFSM=True

    Returns:
        a list of interfaces with 10Mbps
    '''
    # Extract the stack information
    hardware_per_switch = []
    for switch_data in data:
        hardware = switch_data['speed']
        if hardware == '10Mb/s':
            hardware = switch_data['interface'] + ': ' + hardware
            # hardware_per_switch.extend(hardware)
            hardware_per_switch.append(hardware)
    return hardware_per_switch


def switch_type(hardware_per_switch):
    """
    Build a list of switch ports per switch

    Arguments:
        hardware_per_switch -- List returned from function extract_stack_info
    """
    switch_ports = {}
    for count, items in enumerate(hardware_per_switch):
        if '24' in items:
            sw_type = 'switch' + str(count) + ': ' + str(24)
            print(type(sw_type))
            switch_ports = switch_ports.append(sw_type)


def parse_ver(stack_info):
    """
    pull out # of switches and ports per switch

    Arguments:
        stack_info -- a list returned by extract_stack_info funtion

    """


'''
read the command line to find the site name
open the <sitename>-interface.txt file and search for 10Mb/s
interfaces.
'''

System_name = platform.system()
print('OS is ', System_name)

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--site', dest='site_name', help='Site Name')
options = parser.parse_args()
if options.site_name is None:
    print('-s site name is a required argument')
    sys.exit()
else:
    dev_inv_file = 'device-inventory-' + options.site_name

ic(dev_inv_file)

# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print("{} doesn't exist ".format(dev_inv_file))
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file) as devices_file:
    fabric = devices_file.readlines()


for line in fabric:
    hostname = line.split(",")[2]

    loc = get_current_path()
    if System_name == "Darwin" or System_name == "Linux":
        loc = loc + '/interface/'
    else:
        # Windows
        loc = loc + '\\interface\\'

    ver_file = loc + hostname + '-interface.txt'
    ic(ver_file)

    # check if switch's version file exists
    if not os.path.isfile(ver_file):
        print("{} doesn't exist ".format(ver_file))
        sys.exit()

    with open(ver_file, 'r', encoding='utf-8') as inputfile:
        data = json.load(inputfile)

    stack_info = extract_Interface_speed(data)
    for interface in stack_info:
        interface = hostname + ': ' + interface
        print(interface)
