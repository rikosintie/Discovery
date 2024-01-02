# HPE Procurve Discovery Project<!-- omit from toc -->

## Purpose

This project was created to make the discovery process for a network refresh easy, consistent and comprehensive. The discovery data can be used to create a change request for the customer and will make troubleshooting any issues after a switch is replaced easier.

## The Process

The "procurve-Config-pull.py" script uses the <https://github.com/ktbyers/netmiko> library and the Google [textFSM](https://github.com/networktocode/ntc-templates/tree/master) libraries to connect to a switch, run show commands and create JSON files.

Once the data has been collected, there are helper scripts that create port maps, CDP neighbor tables, LLDP neighbor tables, OSPF neighbor tables, etc.

A "show run structured" file is created. There is also a text file of show commands sent. This file can be edited to collect any show commands.

The data is saved to various directories for easy access.
