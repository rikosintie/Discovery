"""
    Creates a csv file from the cdp file with:
    "local_port"
    "neighbor_id"
    "neighbor_address"
    "neighbor_platform"
    "neighbor_port"

    Prints a table to the terminal

Returns:
    Nothing - creates files in CR-data directory
"""

import argparse
import csv
import json
import os
import sys

from icecream import ic

# from prettytable.colortable import ColorTable, Themes
from prettytable import PrettyTable

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
    hostname = line.split(",")[2]

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

    # table = ColorTable(theme=Themes.OCEAN)
    table = PrettyTable()
    table.field_names = cdp_neighbor[0].keys()

    # Add data to the table
    for row in cdp_neighbor:
        table.add_row(row.values())
    # Only print the following columns. neighbor_version is not so useful
    print(
        table.get_string(
            fields=[
                "local_port",
                "neighbor_id",
                "neighbor_address",
                "neighbor_platform",
                "neighbor_capability",
                "neighbor_port",
            ]
        )
    )

    #  Write the cdp output to disk
    int_report = get_current_path("CR-data", "-cdp-data.csv")
    print(f"Writing cdp data to {int_report}")
    with open(int_report, "w") as csv_file:
        csv_writer = csv.writer(csv_file)
        # Write the header
        csv_writer.writerow(table.field_names)
        # Write the data rows
        csv_writer.writerows(table.rows)
