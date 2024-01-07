"""
used to find mac address from a group of switches

Sample output:
=========== Completed Configuration for Index 13 WITH IP 10.200.2.14 at 2023-01-05 09:55:25.968198============

A02-0208XX-SS01# show mac-address-table address 4C:A6:4D:BA:F1:D4
MAC age-time            : 300 seconds
Number of MAC addresses : 1

MAC Address          VLAN     Type                      Port
--------------------------------------------------------------
4c:a6:4d:ba:f1:d4    2        dynamic                   3/1/46
A02-0208XX-SS01#

#MAC on an uplink
A10-1007XX-SS01# show mac-address-table address 4C:A6:4D:BA:F1:D4
MAC age-time            : 300 seconds
Number of MAC addresses : 1

MAC Address          VLAN     Type                      Port
--------------------------------------------------------------
4c:a6:4d:ba:f1:d4    2        dynamic                   lag1
A10-1007XX-SS01#


#No MAC entry
Fullerton8400X-01# show mac-address-table address 4C:A6:4D:BB:C0:8A
No MAC entries found.


FYI is the CSV is in UTF-8 https://stackoverflow.com/questions/17912307/u-ufeff-in-python-string/17912811

https://re-thought.com/how-to-change-or-update-a-cell-value-in-python-pandas-dataframe/amp/


"""

import timeit

start = timeit.default_timer()

import concurrent.futures
import csv
import sys
from datetime import datetime
from getpass import getpass

import pandas as pd
from netmiko import ConnectHandler
from netmiko.exceptions import AuthenticationException, NetmikoTimeoutException


def runCommand():
    with open(filename, "r") as switchInventory:
        df = pd.read_csv(filename, index_col=0, keep_default_na=False)
        for line in csv.DictReader(switchInventory):
            indexID += 1
            ip = line["Address"].strip()
            deviceType = line["OS"].strip()
            hostname = line["Address"].strip()
            # apName = line['AP Name'].strip()
            # switchport_int = line['Neighbor Port'].strip()
            # newVLAN = line['tvvlan'].strip()
            # oldVLAN = line['Old VLAN'].strip()
            isModify = line["Modify"].strip()
            if isModify == "1":
                while not error:
                    try:
                        device_info = {
                            "device_type": deviceType,
                            "ip": ip,
                            "username": username,
                            "password": password,
                        }
                        net_connect = ConnectHandler(**device_info)
                        # commands = [ f'interface {switchport_int}' , 'shutdown' , f'switchport access vlan {newVLAN}' , 'no shutdown' , 'end' , 'wr mem' ]
                        # commands = [ f'interface {switchport_int}' , 'shutdown' ]
                        # commands = [ f'interface {switchport_int}' , 'shutdown' , f'switchport access vlan {oldVLAN}' , 'no shutdown' , 'end' , 'wr mem' ]
                        # commands = [ f'vlan {newVLAN}' , 'name t-fc-voip' , 'voice']
                        macAddress = "4C:A6:4D:BA:F1:D4"
                        showMACAddress = "show mac-address-table address " + macAddress
                        commands = ["\n", showMACAddress]

                        output = net_connect.send_multiline(commands)
                        with open(ip + "_" + hostname + ".txt", "a") as commandInfo:
                            for info in range(len(commands)):
                                commandInfo.write(
                                    net_connect.find_prompt() + commands[info] + "\n"
                                )
                            commandInfo.writelines(output + 2 * "\n")
                        noOfSwitches += 1
                        # net_connect.save_config()
                        net_connect.disconnect()
                        completedTime = datetime.now()
                        df.at[indexID, "Notes"] = "Completed at " + str(completedTime)
                        df.at[indexID, "complete"] = "Yes"
                        print(
                            f"=========== Completed Discovery for Index {indexID} WITH IP {ip} at {completedTime}============"
                        )
                        print(output)
                        # netmiko output when split prints letter by letter when iterating over a for loop.  so first need to split by new line \n
                        outputFiltered = output.split("\n")
                        for line in outputFiltered:
                            if macAddress.lower() in line:
                                port = line.split()[-1]
                                if "/" in port:
                                    print(
                                        f"Switchport found! on {port} on switch with ip of {ip}"
                                    )
                        error = "none"
                    except NetmikoTimeoutException:
                        completedTime = datetime.now()
                        df.at[indexID, "Notes"] = "Timeout at " + str(completedTime)
                        df.at[indexID, "complete"] = "No"
                        print(
                            f"=========== TIMEOUT ERROR for Index {indexID} WITH IP {ip} at {completedTime}============"
                        )
                        error = "timeout"
                        continue
                    except AuthenticationException:
                        completedTime = datetime.now()
                        print(
                            f"========= Authentication Failed for Index {indexID} with {ip} at {completedTime}============"
                        )
                        wrongIPs.append(ip)
                        wrongCredentials.append((username, password))
                        username = getpass(
                            "Incorrect credentials Please enter username for the devices: ",
                            stream=None,
                        )
                        password = getpass(
                            "Incorrect Password Please enter the password for the switches: ",
                            stream=None,
                        )
                        noOfSwitches -= 1
                    except Exception as unknown_error:
                        print(
                            f"============ SOMETHING UNKNOWN HAPPEN WITH {ip} ============"
                        )
                error = ""
            else:
                df.at[indexID, "Notes"] = "SKIPPED, Modify is set to Zero"

    # update CSV File with Notes
    df.to_csv(filename)
    if wrongIPs:
        print("Wrong Credentials Tried:")
        for a, b in zip(wrongIPs, wrongCredentials):
            print("IP: " + a + "  Credentials tried: ", b)
    print(f"{noOfSwitches} switches were searched")
    """
    if commands:
        for info in range(len(commands)):
            print(commands[info])
    """
    return


with concurrent.futures.ThreadPoolExecutor() as exe:
    # init Error Variable
    error = ""
    wrongCredentials = []
    wrongIPs = []
    noOfSwitches = 0
    indexID = 0
    filename = "ac-devices.csv"
    print("Welcome to the network infrastructure discover script!  powered by Netmiko")
    username = getpass("Please enter username for the devices: ", stream=None)
    password = getpass("Please enter password for the devices: ", stream=None)
    results = exe.map(runCommand)

stop = timeit.default_timer()
total_time = stop - start
# output running time in a nice format.
mins, secs = divmod(total_time, 60)
hours, mins = divmod(mins, 60)

sys.stdout.write(
    f"Total running time: {hours} Hours {mins} Minutes {round(secs,2)} Seconds\n"
)

#                    writer = csv.DictWriter(powerInfo)
#                    for line in output:
#                        writeline(line)
