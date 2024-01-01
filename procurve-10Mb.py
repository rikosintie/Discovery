# !!!!! Helper Script - Run on offline data !!!!!

"""
    Reads the interface file created by procurve-Config-pull.py and
    builds a list of interfaces running at 10Mb full or half. Aruba and Cisco smartrate (mGig) ports do not support 10Mb connections.


    Returns:
        Nothing : a file is written to the CR-data directory as hostname-10Mb-Ports.txt
"""

import argparse
import json
import os
import sys

from icecream import ic

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "michael.hubbard99@gmail.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  procurve-10Mb.py
#  Procurve Change Request data collection
#  Created by Michael Hubbard on 2023-28-20.


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


def extract_Interface_speed(json_data: list):
    """
    extract_Interface_speed find interfaces with 10Mbps speed
    10FDx or 10HDx in json data "mode"

    Arguments:
        json_data -- json data from 'show interfaces brief, textFSM=True

    Returns:
        a list of interfaces with 10Mbps
    """
    # Extract the stack information
    hardware_per_switch = []
    for switch_data in data:
        hardware = switch_data["mode"]
        if hardware == "10FDx" or hardware == "10HDx":
            hardware = switch_data["port"] + " - " + hardware
            hardware_per_switch.append(hardware)
    return hardware_per_switch


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


for line in fabric:
    hostname = line.split(",")[2]
    int_report = get_current_path("Interface", "-int_br.txt")
    ic(int_report)

    # check if switch's version file exists
    if not os.path.isfile(int_report):
        print("{} doesn't exist ".format(int_report))
        sys.exit()

    with open(int_report, "r", encoding="utf-8") as file:
        data = json.load(file)

    stack_info = extract_Interface_speed(data)
    if stack_info == []:
        print("No 10Mbps interfaces found")
        SystemExit()

    int_report = get_current_path("CR-data", "-10Mb-Ports.txt")
    print(f"Writing CR data to {int_report}")
    with open(int_report, "w") as file:
        for line in stack_info:
            file.write(f"Interface {line}\n")

    for interface in stack_info:
        print(f"Hostname: {hostname} Interface: {interface}")
