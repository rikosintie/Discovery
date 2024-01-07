[![Commit Activity](https://img.shields.io/github/commit-activity/m/rikosintie/Discovery)](https%3A%2F%2Fgithub.com%2Frikosintie%2FDiscovery)
[![Website](https://img.shields.io/badge/Works_with-Procurve-blue)](https://github.com/rikosintie/CookBook)
[![Website](https://img.shields.io/badge/Blog-Visit-blue)](https://mwhubbard.blogspot.com)
[![License](https://img.shields.io/github/license/rikosintie/Discovery?color=0096FF)](https://github.com/rikosintie/Discovery)
[![X](https://img.shields.io/twitter/follow/rikosintie?style=social&logo=x)](https://twitter.com/rikosintie)

# HPE Procurve Discovery Project<!-- omit from toc -->

- [Purpose](#purpose)
  - [Who is this project for](#who-is-this-project-for)
- [The Process](#the-process)
- [Deployment questions for Discovery](#deployment-questions-for-discovery)
- [License](#license)

There are additional sections to this documentation:

- [Getting Started](https://github.com/rikosintie/Discovery/blob/main/Getting_Started.md)<!-- omit from toc -->
- [Usage](https://github.com/rikosintie/Discovery/blob/main/usage.md)

## Purpose

This project was created to make the discovery process for a network refresh easy, consistent and comprehensive. The discovery data can be used to create a change request, and cut over plan for the customer. The data is also valuable when troubleshooting any issues after a switch is replaced.

You are free to customize the [procurve-config-file.txt](https://github.com/rikosintie/Discovery/blob/main/procurve-config-file.txt) file to add or remove show commands as needed for your discovery.

The script saves the data to various directories for easy access.

### Who is this project for

Anyone that needs to pull data from HPE Procurve switches. You do not need to write any python code. Text files are used to configure the information pulled by the script.

----------------------------------------------------------------

## The Process

The [procurve-Config-pull](https://github.com/rikosintie/Discovery/blob/main/procurve_Config_pull.py) script uses the [netmiko](https://github.com/ktbyers/netmiko) library and the Google [textFSM](https://github.com/networktocode/ntc-templates/tree/master) libraries to connect to a switch, run ***show commands*** and create JSON files.

Once the data has been collected, there are helper scripts that create:

- port maps
- CDP neighbor tables
- LLDP neighbor tables
- OSPF neighbor tables

The Procurve firmware allows you to include the "structured" keyword after the "show running" command. This groups the output in an easier to read format. A [show run structured](https://github.com/rikosintie/Discovery/blob/main/Running/Procurve-2920-24-running-config.txt) file is created in the "Running" directory.

There is also a text file of ***show commands*** sent. This file can be edited to send any show commands you need. The filename is [procurve-config-file.txt](https://github.com/rikosintie/Discovery/blob/main/procurve-config-file.txt).

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

----------------------------------------------------------------

## Deployment questions for Discovery

The script will pull any information that you put into the procurve-config file but it can't answer all the questions! Here are some questions I ask during the kickoff meeting with the customer. Some of these questions are open ended and are meant to get the customer engaged in a conversation about the refresh.

This is not a exhaustive list, feel free to add to it.

- What are the labeling requirements
  - Location
  - What information
  - size
  - material
- What are the asset Tag requirements?
- Is an escort required when we are on site?
- What firmware version should be installed?
- Do you have a standard for host names?
- Does the network team have access to M&O devices such as Environmental monitoring (BACnet), surveillance cameras, door access controls?
- Are we allowed to connect our laptops to the network?
- Can we use tools like nmap and Wireshark to discover devices? Here are some [nmap discovery scripts](https://github.com/rikosintie/nmap-python)
- Is DHCP used for non-server hosts i.e. cameras, door access panels, etc?
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
- Routing protocols
  - Authentication type
  - IPv4
  - IPv6
  - number of areas
- spanning-tree
  - Priority
  - root-guard
  - tcn-guard
  - loop-guard
  - mode
  - admin-edge-port
  - bpdu-protection
  - spanning-tree bpdu-protection-timeout 90
- Rate Limits on edge ports
  - rate-limit bcast
  - rate-limit mcast
  - rate-limit unknown-unicast in
- snmp requirements
  - Version
  - community names
  - location
  - Required traps
- ssh - Old ciphers should be removed
  - Host Key type?
  - Ciphers?
  - MACs?
  - key length?
  - Do you use ssh keys instead of passwords?
- Security
  - DHCP Snooping?
  - Dynamic ARP Inspection
  - Authorized Managers
  - no tftp-server (only scp for copying files)
- Power cord connector requirements
  - NEMA 5-15
  - NEMA L5-20
  - NEMA L6-20
  - IEC C14
  - etc

----------------------------------------------------------------

## License

This project is licensed under the Unlicense - see the LICENSE file for details.

<https://unlicense.org/>
