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
#  procurve-system-report.py
#  Procurve Change Request data collection
#  Created by Michael Hubbard on 2024-1-13.


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
                name = f'{"Hostname: " :>17}{data[counter]["name"]}'
                contact = f'{"snmp contact: " :>17}{data[counter]["contact"]}'

                location = f'{"snmp location: " :>17}{data[counter]["location"]}'

                software_version = (
                    f'{"software_version: " :>17}{data[counter]["software_version"]}'
                )

                rom_version = f'{"rom_version: " :>17}{data[counter]["rom_version"]}'

                mac_address = f'{"mac address: " :>17}{data[counter]["mac_address"]}'

                mac_age = f'{"MAC address age: " :>17}{data[counter]["mac_age"]}'

                serial = f'{"serial number: " :>17}{data[counter]["serial"]}'

                timezone = f'{"timezone: " :>17}{data[counter]["timezone"]}'
                daylight_rule = (
                    f'{"daylight_rule: " :>17}{data[counter]["daylight_rule"]}'
                )

                uptime = f'{"system_uptime: " :>17}{data[counter]["uptime"]}'

                cpu_util = f'{"cpu_utilization: " :>17}{data[counter]["cpu_util"]}'
                mem_free = f'{"mem_free: " :>17}{data[counter]["mem_free"]}'

                divider = "-" * 30
                print()
                # counter += 1
                system = [
                    name,
                    location,
                    contact,
                    mac_age,
                    timezone,
                    daylight_rule,
                    software_version,
                    rom_version,
                    mac_address,
                    serial,
                    uptime,
                    cpu_util,
                    mem_free,
                    "\n",
                    divider,
                ]
                with open(file_path_ne, "a") as file:
                    for item in system:
                        file.write("%s\n" % item)
        # except NameError:
        except Exception as Error:
            print("An error occurred:", type(Error).__name__)
        except KeyboardInterrupt:
            print("ctrl+c was pressed")
            sys.exit()
        except ValueError:
            print(f"Error parsing JSON in file {file_path}:")
