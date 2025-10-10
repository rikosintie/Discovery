# The Network Discovery Project

----------------------------------------------------------------

![screenshot](img/intro4.resized.jpeg)

----------------------------------------------------------------

This project was created to make the discovery process for a network refresh easy, consistent and comprehensive. The discovery data can be used to create a change request, and cut over plan for the customer. The data is also valuable when troubleshooting any issues after a switch is replaced.

The project currently supports the following devices:

- HPE Procurve
- Cisco IOS
- Cisco XE
- Cisco Nexus
- Aruba CX

A plain text file is used to store the `show commands` that are sent to the switches. An example file for an HPE Procurve switch can be found [here](https://github.com/rikosintie/Discovery/blob/main/procurve-config-file.txt). You are free to customize the file by adding or removing show commands as needed for your discovery.  The script saves the data to various directories for easy access.

## Who is this project for

Anyone that needs to pull data from HPE Procurve, Cisco IOS or Aruba CX switches. You do not need to write any python code. Text files are used to collect the information used by the script. You do not need to be a Python programmer to use this project.

----------------------------------------------------------------

## The Process

There are two types of scripts in the project:

- Discovery - These are scripts that use netmiko to connect to a switch and pull down data. No configuration commands are sent so the script is safe to use in production.
- Helper - These are scripts that take the data that was collected with the discovery script and convert usable reports. They are run offline and do not make any changes to the switches.

The python discovery script [config-pull.py](https://github.com/rikosintie/Discovery/blob/main/config_pull.py) uses the industry standard  [netmiko](https://github.com/ktbyers/netmiko) Python library and the Network to Code [textFSM](https://github.com/networktocode/ntc-templates/tree/master) libraries to connect to a switch, run ***show commands*** and create JSON files. These two libraries hide the complexity of connecting to and interacting with network devices.

### show commands

The show commands are saved to a file named {vendor-id}-config-file.txt, where vendor-id is:

- hp_procurve
- cisco_ios
- cisco_xe
- cisco_nx
- aruba_cx

.  This file can be edited to send any show commands you need.

The format is:

`show 'command'` with each command on a separate line. Here is a snippet of the file:

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

I like the output of this command. You can see vlan id, vlan name, IP Address, IP Mask, Config method, state, voice and jumbo all in one table. This would make a nice alias on the switch.

`alias "vlan" "show vlan custom id name:15 ipaddr ipmask ipconfig state voice jumbo"`

### What are the JSON files used for

Once the data has been collected, there are helper scripts that use the JSON structured data to create:

- CDP neighbor tables
- LLDP neighbor tables
- OSPF neighbor tables

### Port Maps

There is also a helper script that reads the arp table of the layer 3 switch and creates a dictionary of mac address to IP address. Then reads the `show mac address-table interface` data and creates a port map. Here is a sample of what it looks like:

```bash
Number of Entries: 249

Device Name: JC-IDF-1
Vlan   IP Address       MAC Address                  Interface             Vendor
--------------------------------------------------------------------------------
 100   10.100.126.35    1418.7736.5c5d    dynamic    TenGigabitEthernet1/1 Dell
--------------------------------------------------------------------------------
 100   10.100.126.57    14b3.1f0b.61da    dynamic    TenGigabitEthernet1/1 Dell
--------------------------------------------------------------------------------
 100   10.100.126.237   38ed.18ec.ccc1    dynamic    TenGigabitEthernet1/1 Cisco
--------------------------------------------------------------------------------
 100   10.100.126.136   4487.fc94.9d02    dynamic    TenGigabitEthernet1/1 Elitegro

```

The port maps help with planning before a cutover and troubleshooting after a cutover.

### show running-config

A `show running-configuration` is saved to the "Running" directory for each switch. The Procurve firmware allows you to include the "structured" keyword after the "show running-configuration" command. This groups the output in an easier to read format. For Procurve switches, a [show run structured](https://github.com/rikosintie/Discovery/blob/main/Running/Procurve-2920-24-running-config.txt) file is created in the "Running" directory.

----------------------------------------------------------------

## "Standard" Commands?

This script started out to pull configs from Cisco 3750x switches. I was on a long term contract at a customer with about 500 Cisco 3750x switches and was migrating to Aruba 6300CX switches.

The script was a life saver pulling all the Change Request data automatically. I then used a great library called `cisco_config_parse` to read the Cisco running-configuration and convert it to Aruba CX format.

When that contract ended I needed to do a refresh at customer that had HPE Procurve switches. I thought "how hard could it be to add Procurve?" Well, it turned out to be an adventure. And then I wanted to pull some Cisco SG small business switch configs, then some Cisco XE. Wow, every vendor has a different way of naming commands. Here is a table that I started so that I could expand the script to cover almost any customer. You can see the problem of adding a new vendor to the mix. And any new vendor has to be supported by Netmiko and Google TextFSM. It's really a nightmare.

Then to create a port-map of IP, Vlan, Manufacturer I have to pull the mac-address table and parse it. But that is another challenge because:

- hp_procurve - aabbcc-ddeeff
- cisco ios - aabb.ccdd.eeff
- aruba_cx - aa\:bb\:cc\:dd\:ee\:ff
- Windows aa-bb-cc-dd-ee-ff

I finally wrote a python script to convert mac addresses from any format to all formats. It's named `convert-mac.py` and it gets installed when you clone the Discovery repo.

Currently I only have Procurve, cisco_ios and cisco_xe fully implemented.

| Task                     | Cisco IOS                                | Cisco NX-OS                              | Cisco SG/SGX (Small Biz)              | HP ProCurve                          | Juniper                              | Brocade                              | Dell N1500                            | Aruba CX                              |
|--------------------------|-------------------------------------------|-------------------------------------------|----------------------------------------|---------------------------------------|----------------------------------------|----------------------------------------|----------------------------------------|----------------------------------------|
| Show MAC address         | `show mac address-table` / `show mac-address` | `show mac address-table`                  | `show mac-address-table`               | `show mac-address`                    | `show ethernet-switching table`       | `show mac-address`                     | `show mac address-table`               | `show mac-address-table`               |
| Show uptime              | `show version` (parse output)             | `show system uptime`                      | `show system` or GUI only               | `show system information`             | `show system uptime`                  | `show system uptime`                   | `show system`                          | `show system`                          |
| Show model/serial        | `show inventory` / `show version`         | `show version` or `show sprom`            | `show system`                           | `show system information`             | `show chassis hardware`               | `show chassis`                         | `show system` or `show version`        | `show system`                          |
| Show LLDP neighbors      | `show lldp neighbors detail`              | `show lldp neighbors`                     | Not supported or limited via GUI        | `show lldp info remote detail`        | `show lldp neighbors detail`          | `show lldp neighbors`                  | `show lldp neighbors`                  | `show lldp neighbors detail`           |

----------------------------------------------------------------

## Questions for Discovery and Deployment

The script will pull any information that you put into the `<vendor-id>-config-file.txt` file but it can't answer all the questions! Here are some questions I ask during the kickoff meeting with the customer. Some of these questions are open ended and are meant to get the customer engaged in a conversation about the refresh.

This is not an exhaustive list, feel free to add to it.

1. What are the labeling requirements
    a. Location on the equipment
    b. What information
    c. size
    d. material

2. What are the Asset Tag requirements for switches, routers, servers?
3. Is an escort required when we are on site?
4. How is access (Keys, codes, alarm codes, etc) granted?
5. If after hours cut overs are required, who is the after hours contact?
6. Will VPN be provided?
7. When on site:
    1. Are we allowed to connect our laptops to the network?
    1. If not, will a jumpbox be provided?
    1. If using a jumpbox can we install tools like python or nmap?
8. Can we use tools like nmap and Wireshark to discover devices?
    1. Here are some [nmap scripts](https://github.com/rikosintie/nmap-python) that I wrote for discovery.
9. Is a change request document required?
    1. If so, how many days before the cut over?
    1. Who creates the document?
    1. Is there a template for the change request document?
    1. Who approves the document?
    1. Who will do the post cut over testing?
    1. How long after the cut over until a sign off is completed?
10. If a monitoring tool such as Solarwinds Orion in use:
    1. Who disables alerts for the devices being cut over?
    1. Will we have access to monitor progress during the cut over?
    1. Is a syslog server available that we can access?
11. Firmware
    1. What firmware version should be installed?
    1. If the project spans months, will switches be put on the current firmware before being deployed?
    1. Who will upgrade the switches that have already been deployed?
12. Does the network team have access to M&O devices such as Environmental monitoring (BACnet), surveillance cameras, door access controls?
13. Is DHCP used for non-server hosts i.e. cameras, door access panels, etc?
14. If ClearPass will be used, DHCP allows devices to be profiled.
15. Do you have a standard for host names?
    1. A refresh is a good time to make a host name changes if needed.
16. Do you have a management vlan?
    1. If so, what are the management vlan IP addresses?
    1. default gateway or gateway of last resort IP address?
17. Authentication Server
    1. Authentication Server IP address
    1. Authentication Server credentials
18. NTP Server
    1. IP address
    1. Authentication credentials
19. Username/password for base configuration installation
    1. Enable password for base configuration
    2. Hashing type - scrypt recommeded :arrow: username Your-User algorithm-type scrypt secret Cleartext-Password
20. Power cord connector requirements
    1. NEMA 5-15 (Standard 120v plug)
    2. NEMA L5-20 (120v twistlok plug)
    3. NEMA L6-20 (240v twistlok plug)
    4. IEC C14 (PDU Style plug)
21. Routing protocols
    1. Authentication type - Highly recommend using authentication to prevent takeover.
    2. IPv4
    3. IPv6 - If iPv6 isn't used, P2P routers are a good place to start
    4. number of areas
22. Rate Limits on edge ports
    1. rate-limit broadcast
    2. rate-limit multicast
    3. rate-limit unknown-unicast
23. Security
    1. DHCP Snooping - Highly recommended, low effort to deploy
    2. Dynamic ARP Inspection - Highly recommended. High effort to deploy
    3. Authorized Managers - highly recommended
    4. no tftp-server (only scp for copying files)
24. snmp requirements
    1. Version - V3 highly recommeded
    2. community names
    3. location
    4. Required traps
25. What are the spanning-tree requirements?
    1. Priority - Core should be lowest
    2. root-guard - recommended
    3. tcn-guard
    4. loop-guard
    5. mode - RPVST recommended
    6. admin-edge-port
    7. bpdu-protection - recommended
    8. spanning-tree bpdu-protection-timeout 90
26. ssh - Old ciphers should be removed
    1. Host Key type - ssh-rsa recommended
    2. Ciphers - aes256-ctr recommended
    3. MACs- hmac-sha2-512,hmac-sha2-256 recommended
    4. key length - 2048 or larger recommended
    5. Do you use ssh keys instead of passwords?

!!! Note Cisco hashing
    `test(config)#username mhubbard secret ?`
    - 0      Specifies an UNENCRYPTED secret will follow
    - 5      Specifies a MD5 HASHED secret will follow
    - 8      Specifies a PBKDF2 HASHED secret will follow
    - 9      Specifies a SCRYPT HASHED secret will follow
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

## Security Policy

Click here to open the [Security Policy](https://github.com/rikosintie/Discovery/blob/main/security.md)

----------------------------------------------------------------
