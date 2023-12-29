'''
!!!!! Helper Script !!!!!!

    Creates a text file from the cdp file with:
    "destination_host"
    "management_ip"
    "platform"
    "remote_port"
    "local_port":
    "software_version":

Returns:
    Nothing - creates files in the ospf-data\neighbors folder.
'''

# !!!!! Helper Script !!!!!!

from icecream import ic
import os
import json
import sys

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"


def get_current_path():
    current_path = os.getcwd()
    return current_path

# Read the ospf neighbor file to pull in the stack count
loc = get_current_path()

loc = loc + '\\ospf-data\\'
loc1 = loc + '\\neighbors\\'



file_list = [f for f in os.listdir(loc) if f.endswith('cdp_ne.txt')]

for file_name in file_list:
    file_name_ne = file_name[0:-10]
    file_name_ne = file_name_ne + 'cdp-ne.txt'
    file_path = os.path.join(loc, file_name)
    file_path_ne = os.path.join(loc1, file_name_ne)
    with open(file_path, 'r') as file:
        try:
            data = json.load(file)
            osfp_neighbors = []
            counter = 0
            for value in data:
                # print(file_name)
                # print("neighbor id: " + data[counter]['neighbor_id'])
                # print('state: ' + data[counter]['state'])
                # print('address: ' + data[counter]['address'])
                # print('interface: ' + data[counter]['interface'])
                # print('-' * 30)
                # print()
                fname = file_name
                destination_host = "destination_host: " + data[counter]['destination_host']
                management_ip = 'management_ip: ' + data[counter]['management_ip']
                platform = 'platform: ' + data[counter]['platform']
                remote_port = 'remote_port: ' + data[counter]['remote_port']
                local_port = 'local_port: ' + data[counter]['local_port']
                software_version = 'software_version: ' + data[counter]['software_version']
                divider = ('-' * 30)
                print()
                counter += 1
                osfp_neighbors = [destination_host, management_ip, platform, remote_port, local_port, software_version,'\n', divider]
                with open(file_path_ne, 'a') as file:
                    for item in osfp_neighbors:
                        file.write('%s\n' % item)
        except NameError:
            print(f'Error parsing JSON in file {file_path}:')
    # Reset print function to default
