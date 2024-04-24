[![Commit Activity](https://img.shields.io/github/commit-activity/m/rikosintie/Discovery)](https%3A%2F%2Fgithub.com%2Frikosintie%2FDiscovery)
[![Website](https://img.shields.io/badge/Works_with-Procurve-blue)](https://github.com/rikosintie/CookBook)
[![Website](https://img.shields.io/badge/Blog-Visit-blue)](https://mwhubbard.blogspot.com)
[![License](https://img.shields.io/github/license/rikosintie/Discovery?color=0096FF)](https://github.com/rikosintie/Discovery)
[![X](https://img.shields.io/twitter/follow/rikosintie?style=social&logo=x)](https://twitter.com/rikosintie)

# Pterodactyl Network  Discovery Project<!-- omit from toc -->
<p align="left" width="30%">
<img width="30%" src="https://github.com/rikosintie/Discovery/blob/main/images/pterodactyl.jpeg" alt="Pterodactyl">
</p>
- [Purpose](#purpose)
  - [Who is this project for](#who-is-this-project-for)
- [The Process](#the-process)
  - [show commands](#show-commands)
  - [What are the JSON files used for](#what-are-the-json-files-used-for)
  - [show running-config](#show-running-config)
- [Questions for Discovery and Deployment](#questions-for-discovery-and-deployment)
- [License](#license)
- [SBOM - a Software Bill of Materials](#sbom---a-software-bill-of-materials)

There are additional sections to this documentation:

- [Getting Started](https://github.com/rikosintie/Discovery/blob/main/Getting_Started.md)<!-- omit from toc -->
- [Usage](https://github.com/rikosintie/Discovery/blob/main/usage.md)
- [The Helper Scripts](https://github.com/rikosintie/Discovery/blob/main/Helper-scripts.md)

## Purpose

This project was created to make the discovery process for a network refresh easy, consistent and comprehensive. The discovery data can be used to create a change request, and cut over plan for the customer. The data is also valuable when troubleshooting any issues after a switch is replaced.

A plain text file [procurve-config-file.txt](https://github.com/rikosintie/Discovery/blob/main/procurve-config-file.txt) is used to store the `show commands` that are sent to the switches. You are free to customize the [procurve-config-file.txt](https://github.com/rikosintie/Discovery/blob/main/procurve-config-file.txt) file to add or remove show commands as needed for your discovery.

The script saves the data to various directories for easy access.

### Who is this project for

Anyone that needs to pull data from HPE Procurve switches. You do not need to write any python code. Text files are used to configure the information used by the script.

----------------------------------------------------------------

## The Process

There are two types of scripts in the project:

- Discovery - These are switches that use netmiko to connect to a switch and pull down data.
- Helper - These are scripts that take JSON data that was collected with the discovery script and convert it into human readable format.

The python discovery script [procurve-Config-pull.py](https://github.com/rikosintie/Discovery/blob/main/procurve_Config_pull.py) uses the [netmiko](https://github.com/ktbyers/netmiko) library and the Google [textFSM](https://github.com/networktocode/ntc-templates/tree/master) libraries to connect to a switch, run ***show commands*** and create JSON files.

### show commands

The show commands are saved to a file named [procurve-config-file.txt](https://github.com/rikosintie/Discovery/blob/main/procurve-config-file.txt). This file can be edited to send any show commands you need.

The format is:

`show command` with each command on a separate line. Here is a snippet of the file:

```bash
show system
show config status
show oobm
show oobm ip
```

The show commands are saved to the CR-data directory using the format [hostname]-CR-data.txt. For example, if the hostname is "Procurve-2920-24" the filename is Procurve-2920-24-CR-data.txt.

On the Procurve switches you can customize the output of show vlans. This HPE Techpub article shows how to do it:

[Customizing the show VLANs output](https://techhub.hpe.com/eginfolib/networking/docs/switches/K-KA-KB/15-18/atmg/content/ch01s06.html)

The procurve-config-file.txt uses the following customizations:

```bash
show vlan custom id name:15 ipaddr ipmask ipconfig state voice jumbo

Status and Counters - VLAN Information - Custom view

 VLANID VLAN name       IP Addr         IP Mask         IPConfig   State Voice Jumbo
 ------ --------------- --------------- --------------- ---------- ----- ----- -----
 1      DEFAULT_VLAN                                    DHCP/Bootp Up    No    No
 10     User            192.168.10.52   255.255.255.0   Manual     Up    No    No
 20     Voice           10.164.24.200   255.255.255.0   Manual     Up    Yes   No
 60     IOT0            10.14.66.17     255.255.255.248 Manual     Up    No    No
 61     IOT1            10.14.65.17     255.255.255.248 Manual     Up    No    No
 62     IOT2            10.14.64.17     255.255.255.248 Manual     Up    No    No
 63     IOT3            10.14.63.17     255.255.255.248 Manual     Up    No    No
 100    test            10.10.100.1     255.255.255.0   Manual     Down  No    No
 850    OSPF-Peering    10.254.34.18    255.255.255.252 Manual     Up    No    No
```

I like output of this command. You can see vlan id, vlan name, IP Address, IP Mask, Config method, state, voice and jumbo all in one table. This would make a nice alias on the switch.

`alias "vlan" "show vlan custom id name:15 ipaddr ipmask ipconfig state voice jumbo"`

### What are the JSON files used for

Once the data has been collected, there are helper scripts that use the JSON structured data to create:

- CDP neighbor tables
- LLDP neighbor tables
- OSPF neighbor tables

### show running-config

The Procurve firmware allows you to include the "structured" keyword after the "show running" command. This groups the output in an easier to read format. A [show run structured](https://github.com/rikosintie/Discovery/blob/main/Running/Procurve-2920-24-running-config.txt) file is created in the "Running" directory.

----------------------------------------------------------------

## Questions for Discovery and Deployment

The script will pull any information that you put into the procurve-config file but it can't answer all the questions! Here are some questions I ask during the kickoff meeting with the customer. Some of these questions are open ended and are meant to get the customer engaged in a conversation about the refresh.

This is not a exhaustive list, feel free to add to it.

- What are the labeling requirements
  - Location
  - What information
  - size
  - material
- What are the asset Tag requirements?
- Is an escort required when we are on site?
- How is access (Keys, codes, alarm codes, etc) granted?
- If after hours cut overs are required, who is the after hours contact?
- Are we allowed to connect our laptops to the network?
- Can we use tools like nmap and Wireshark to discover devices?
  - Here are some [nmap scripts](https://github.com/rikosintie/nmap-python) that I wrote for discovery.
- Is a change request document required?
  - If so, how many days before the cut over?
  - Who creates the document?
  - Is there a template for the change request document?
- Who will do the post cut over testing?
- How long after the cut over until a sign off is completed?
- If a monitoring tool such as Solarwinds Orion in use:
  - Who disables alerts for the devices being cut over?
  - Will we have access to monitor progress during the cut over?
- Is a syslog server available that we can access?
- Firmware
  - What firmware version should be installed?
  - If the project spans months, will switches be put on the current firmware before being deployed?
  - Who will upgrade the switches that have already been deployed?
- Does the network team have access to M&O devices such as Environmental monitoring (BACnet), surveillance cameras, door access controls?
- Is DHCP used for non-server hosts i.e. cameras, door access panels, etc?
  - If ClearPass will be used, DHCP allows devices to be profiled.
- Do you have a standard for host names?
  - A refresh is a good time to make a host name changes if needed.
- Do you have a management vlan?s
  - If so, what are the management vlan IP addresses?
- default gateway or gateway of last resort IP address?
- Authentication Server IP address
- Authentication Server credentials
- NTP Server
  - IP address
  - Authentication credentials
- Username/password for base configuration installation
- Enable password for base configuration
- Power cord connector requirements
  - NEMA 5-15 (Standard 120v plug)
  - NEMA L5-20 (120v twistlok plug)
  - NEMA L6-20 (240v twistlok plug)
  - IEC C14 (PDU Style plug)
- Routing protocols
  - Authentication type
  - IPv4
  - IPv6
  - number of areas
- Rate Limits on edge ports
  - rate-limit bcast
  - rate-limit mcast
  - rate-limit unknown-unicast in
- Security
  - DHCP Snooping?
  - Dynamic ARP Inspection
  - Authorized Managers
  - no tftp-server (only scp for copying files)
- snmp requirements
  - Version
  - community names
  - location
  - Required traps
- What are the spanning-tree requirements?
  - Priority
  - root-guard
  - tcn-guard
  - loop-guard
  - mode
  - admin-edge-port
  - bpdu-protection
  - spanning-tree bpdu-protection-timeout 90
- ssh - Old ciphers should be removed
  - Host Key type?
  - Ciphers?
  - MACs?
  - key length?
  - Do you use ssh keys instead of passwords?

----------------------------------------------------------------

## License

This project is licensed under the Unlicense - see the LICENSE file for details.

<https://unlicense.org/>

----------------------------------------------------------------

## SBOM - a Software Bill of Materials

Github has a feature for creating an SPDX compatible SBOM file. From the repository page click:
Insights, Dependency Graph, Export SBOM.

This project includes a file named sbom.json.

You can use tools from the [SPDX project](https://github.com/spdx/tools-python) to validate and work with the sbom.json file. They have a python script that allows you to output a Graphviz format file. Here is the command I used to create sbom.dot.

`pyspdxtools -i sbom.json --graph -o sbom``

You can use this site, [Graphviz Visual Editor](http://magjac.com/graphviz-visual-editor/) to convert the sbom.dot file to an SVG image. For this project the filename is spdx.svg.

----------------------------------------------------------------

[Home - ](https://github.com/rikosintie/Discovery/)<!-- omit from toc -->
[Getting Started - ](https://github.com/rikosintie/Discovery/blob/main/Getting_Started.md)<!-- omit from toc -->
[Usage - ](https://github.com/rikosintie/Discovery/blob/main/usage.md)<!-- omit from toc -->
[The Helper Scripts](https://github.com/rikosintie/Discovery/blob/main/Helper-scripts.md)<!-- omit from toc -->
