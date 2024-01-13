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
import sys

from icecream import ic

# ic.enable()
ic.disable()

__author__ = "Michael Hubbard"
__author_email__ = "mhubbard@vectorusa.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  procurve-lldp-ne-report.py
#  Procurve Change Request data collection
#  Created by Michael Hubbard on 2024-1-12.


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

            for counter, value in enumerate(data):
                fname = file_name
                neighbor_sysname = (
                    f'{"neighbor_sysname: " :>29}{data[counter]["neighbor_sysname"]}'
                )
                neighbor_chassis_type = f'{"neighbor_chassis_type: " :>29}{data[counter]["neighbor_chassis_type"]}'

                neighbor_chassis_id = f'{"neighbor_chassis_id: " :>29}{data[counter]["neighbor_chassis_id"]}'

                remote_management_address = f'{"remote_management_address: " :>29}{data[counter]["remote_management_address"]}'

                neighbor_portid = (
                    f'{"neighbor_portid: " :>29}{data[counter]["neighbor_portid"]}'
                )
                local_port = f'{"local_port: " :>29}{data[counter]["local_port"]}'

                system_descr = f'{"system_descr: " :>29}{data[counter]["system_descr"]}'
                pvid = f'{"PVID: " :>29}{data[counter]["pvid"]}'

                port_descr = f'{"port_descr: " :>29}{data[counter]["port_descr"]}'
                system_capabilities_enabled = f'system_capabilities_enabled: {data[counter]["system_capabilities_enabled"]}'

                divider = "-" * 30
                print()
                # counter += 1
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
        # except NameError:
        except Exception as Error:
            print("An error occurred:", type(Error).__name__)
        except KeyboardInterrupt:
            print("ctrl+c was pressed")
            sys.exit()
        except ValueError:
            print(f"Error parsing JSON in file {file_path}:")
