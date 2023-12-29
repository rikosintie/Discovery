'''
    Creates a text file from the cdp file with:
    "destination_host"
    "management_ip"
    "platform"
    "remote_port"
    "local_port":
    "software_version":

Returns:
    Nothing - creates files in 
'''

from icecream import ic
# import re
import sys
import os
import argparse
# import sys
import json
# import csv
# import pandas as pd

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


# read the command line to find the site name
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--site", help="Site name - ex. MVMS")
args = parser.parse_args()
site = args.site

if site is None:
    print('-s site name is a required argument')
    sys.exit()
else:
    dev_inv_file = 'device-inventory-' + site
    
ic(dev_inv_file)

# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print("{} doesn't exist ".format(dev_inv_file))
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file) as devices_file:
    fabric = devices_file.readlines()

uptime = []
for line in fabric:
    # line = line.strip("\n")
    # ipaddr = line.split(",")[0]
    # vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    # username = line.split(",")[3]
    # password = line.split(",")[4]

    #
    loc = get_current_path()
    loc = loc + '\\interface\\'
    cdp_file = loc + hostname + '-cdp.txt'
    ic(cdp_file)

    # check if site's device inventory file exists
    if not os.path.isfile(cdp_file):
        print("{} doesn't exist ".format(cdp_file))
        # sys.exit()
        continue

    cdp_neighbor = {}
    with open(cdp_file, 'r', encoding='utf-8') as inputfile:
        cdp_neighbor = json.load(inputfile)

    for value in cdp_neighbor:
        if 'cisco WS' in value['platform']:
            print(f'{hostname},{value["destination_host"]},{value["management_ip"]},{value["platform"]}')
