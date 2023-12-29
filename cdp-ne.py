"""
    Creates a text file from the cdp file with:
    "neighbor_id"
    "neighbor_address"
    "neighbor_platform"
    "neighbor_port"
    "local_port":
    "neighbor_version":

Returns:
    Nothing - creates files in CR-data directory
"""

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
#  cdp-ne.py
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


# read the command line to find the site name
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--site", help="Site name - ex. HQ")
args = parser.parse_args()
site = args.site

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    dev_inv_file = "device-inventory-" + site + ".csv"

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
    # loc = get_current_path()
    # loc = loc + "\\interface\\"
    # cdp_file = loc + hostname + "-cdp.txt"
    cdp_file = get_current_path("Interface", "-cdp.txt")
    ic(cdp_file)

    # check if site's cdp file exists
    if not os.path.isfile(cdp_file):
        print("{} doesn't exist ".format(cdp_file))
        # sys.exit()
        continue

    cdp_neighbor = {}
    with open(cdp_file, "r", encoding="utf-8") as file:
        cdp_neighbor = json.load(file)

    print("     Port    Hostname     IP Address Platform   interface  software")

    for value in cdp_neighbor:
        # if "cisco WS" in value["platform"]:
        print(
            f'{hostname}: {value["local_port"]},  {value["neighbor_id"]},{value["neighbor_address"]},{value["neighbor_platform"]}, {value["neighbor_port"]}, {value["neighbor_version"]}'
        )
