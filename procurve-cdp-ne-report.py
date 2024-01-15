"""
!!!!! Helper Script !!!!!!

    Creates a text file from the cdp file with:
    "neighbor_id"
    "neighbor_address"
    "neighbor_platform"
    "neighbor_port"
    "local_port":
    "neighbor_version":

Returns:
    Nothing - creates files in the Interface\neighbors folder.
"""

# !!!!! Helper Script !!!!!!

import json
import os

from icecream import ic

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  procurve-cdp-ne-report.py
#  Procurve Change Request data collection
#  Created by Michael Hubbard on 2024-1-11.


# Build path to Interface/neighbors and build list of cdp files
loc = os.path.join("Interface")
loc1 = os.path.join("Interface", "neighbors")
file_list = [f for f in os.listdir(loc) if f.endswith("cdp.txt")]

for file_name in file_list:
    file_name_ne = file_name[0:-7]
    file_name_ne = file_name_ne + "cdp-report.txt"
    file_path = os.path.join(loc, file_name)
    file_path_ne = os.path.join(loc1, file_name_ne)
    if os.path.exists(file_path_ne):
        os.remove(file_path_ne)
    with open(file_path, "r") as file:
        try:
            data = json.load(file)
            cdp_neighbors = []
            counter = 0
            for value in data:
                fname = file_name
                destination_host = (
                    f'{"destination_host: " :>18}{data[counter]["neighbor_id"]}'
                )
                management_ip = (
                    f'{"management_ip: " :>18}{data[counter]["neighbor_address"]}'
                )
                platform = f'{"platform: " :>18}{data[counter]["neighbor_platform"]}'
                remote_port = f'{"remote_port: " :>18}{data[counter]["neighbor_port"]}'
                local_port = f'{"local_port: " :>18}{data[counter]["local_port"]}'
                software_version = (
                    f'{"software_version: " :>18}{data[counter]["neighbor_version"]}'
                )
                divider = "-" * 30
                print()
                counter += 1
                cdp_neighbors = [
                    destination_host,
                    management_ip,
                    platform,
                    remote_port,
                    local_port,
                    software_version,
                    "\n",
                    divider,
                ]
                with open(file_path_ne, "a") as file:
                    for item in cdp_neighbors:
                        file.write("%s\n" % item)
        except NameError:
            print(f"Error parsing JSON in file {file_path}:")
