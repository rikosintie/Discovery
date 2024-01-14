# !!!!! Helper Script - Run on offline data !!!!!

import argparse
import json
import os
import sys

from icecream import ic

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  procurve-interface-in-use.py
#  Procurve Change Request data collection Helper program
#  Created by Michael Hubbard on 2023-27-20.


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


def remove_empty_lines(filename: str):
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


def extract_Interface_bytes(json_data: list):
    """
    extract_Interface_bytes find interfaces total_bytes in json data "total_bytes"

    Arguments:
        json_data -- json data from 'show interfaces, textFSM=True

    Returns:
        a list of interfaces with total_bytes
    """

    hardware_per_switch = []
    count: int = 0
    for switch_data in data:
        bytes = switch_data["total_bytes"]
        interface_data = switch_data["port"] + " - " + "total_bytes " + bytes
        hardware_per_switch.append(interface_data)
        if bytes != "0":
            count += 1
    return hardware_per_switch, count


"""
read the command line to find the site name
open the <sitename>-int_br.txt file and search for 10FDx or 10HDx
interfaces.
"""


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--site", dest="site_name", help="Site Name")
options = parser.parse_args()
if options.site_name is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    dev_inv_file = "device-inventory-" + options.site_name + ".csv"

ic(dev_inv_file)

# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print("{} doesn't exist ".format(dev_inv_file))
    sys.exit()

remove_empty_lines(dev_inv_file)

with open(dev_inv_file) as devices_file:
    fabric = devices_file.readlines()

# Build path to Interface/neighbors and build list of system files
loc = os.path.join("Interface")
loc1 = os.path.join("Interface", "neighbors")
file_list = [f for f in os.listdir(loc) if f.endswith("system.txt")]

for file_name in file_list:
    file_name_ne = file_name[0:-10]
    file_name_ne = file_name_ne + "system-report.txt"
    file_path = os.path.join(loc, file_name)
    file_path_ne = os.path.join(loc1, file_name_ne)
    if os.path.exists(file_path_ne):
        os.remove(file_path_ne)
    with open(file_path, "r") as file:
        try:
            data = json.load(file)
            system = []

            for counter, value in enumerate(data):
                fname = file_name
                uptime = f'\n{"System Uptime: "}{data[counter]["uptime"]}\n\n'
        except Exception as Error:
            print("An error occurred:", type(Error).__name__)
        except KeyboardInterrupt:
            print("ctrl+c was pressed")
            sys.exit()
        except ValueError:
            print(f"Error parsing JSON in file {file_path}:")

for line in fabric:
    hostname = line.split(",")[2]
    int_report = get_current_path("Interface", "-interface.txt")
    ic(int_report)

    # check if switch's interface file exists
    if not os.path.isfile(int_report):
        print("{} doesn't exist ".format(int_report))
        sys.exit()

    with open(int_report, "r", encoding="utf-8") as file:
        data = json.load(file)

    stack_info, count = extract_Interface_bytes(data)
    if stack_info == []:
        print("No interfaces with 0 Total_Bytes found")
        sys.exit()

    int_report = get_current_path("CR-data", "-Port-data.txt")
    print(f"Writing CR data to {int_report}")
    with open(int_report, "w") as file:
        file.write(uptime)
        file.write(f"Number of Interfaces with traffic: {count}\n")
        for line in stack_info:
            file.write(f"Interface {line}\n")

    print()
    print(f"Number of Interfaces with traffic: {count}\n")
    for interface in stack_info:
        print(f"Hostname: {hostname} Interface: {interface}")
