"""
!!!!! Helper Script !!!!!!

    Creates a text file from the lldp file with:
    "local_port":
    "neighbor_chassis_type"
    "neighbor_chassis_id"
    "neighbor_portid"
    "neighbor_sysname"
    "system_descr"
    "pvid"
    "system_capabilities_enabled"
    "remote_management_address"
    "system_capabilities_enabled"





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


def get_current_path(sub_dir1: str, extension: str = "", sub_dir2="") -> str:
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


# Build path to Interface/neighbors and build list of cdp files
loc = os.path.join("Interface")
loc1 = os.path.join("Interface", "neighbors")
file_list = [f for f in os.listdir(loc) if f.endswith("lldp.txt")]

for file_name in file_list:
    file_name_ne = file_name[0:-8]
    file_name_ne = file_name_ne + "lldp-report.txt"
    file_path = os.path.join(loc, file_name)
    file_path_ne = os.path.join(loc1, file_name_ne)
    if os.path.exists(file_path_ne):
        os.remove(file_path_ne)
    with open(file_path, "r") as file:
        try:
            data = json.load(file)
            lldp_neighbors = []
            counter = 0
            for value in data:
                fname = file_name
                neighbor_chassis_type = (
                    "      neighbor_chassis_type: "
                    + data[counter]["neighbor_chassis_type"]
                )
                neighbor_chassis_id = (
                    "        neighbor_chassis_id: "
                    + data[counter]["neighbor_chassis_id"]
                )
                remote_management_address = (
                    "  remote_management_address: "
                    + data[counter]["remote_management_address"]
                )
                neighbor_sysname = (
                    "           neighbor_sysname: " + data[counter]["neighbor_sysname"]
                )
                neighbor_portid = (
                    "            neighbor_portid: " + data[counter]["neighbor_portid"]
                )
                local_port = (
                    "                 local_port: " + data[counter]["local_port"]
                )
                system_descr = (
                    "               system_descr: " + data[counter]["system_descr"]
                )
                pvid = "                       PVID: " + data[counter]["pvid"]
                port_descr = (
                    "                 port_descr: " + data[counter]["port_descr"]
                )
                system_capabilities_enabled = (
                    "system_capabilities_enabled: "
                    + data[counter]["system_capabilities_enabled"]
                )
                divider = "-" * 30
                print()
                counter += 1
                lldp_neighbors = [
                    neighbor_sysname,
                    remote_management_address,
                    neighbor_chassis_type,
                    neighbor_chassis_id,
                    system_descr,
                    neighbor_portid,
                    local_port,
                    system_descr,
                    pvid,
                    port_descr,
                    system_capabilities_enabled,
                    "\n",
                    divider,
                ]
                with open(file_path_ne, "a") as file:
                    for item in lldp_neighbors:
                        file.write("%s\n" % item)
        except NameError:
            print(f"Error parsing JSON in file {file_path}:")
