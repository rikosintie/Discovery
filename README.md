# HPE Procurve Discovery Project<!-- omit from toc -->

- [Purpose](#purpose)
- [The Process](#the-process)
- [Deployment questions for Discovery](#deployment-questions-for-discovery)
- [Getting Started](#getting-started)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Create a Virtual Environment](#2-create-a-virtual-environment)
  - [3. Activate the Virtual Environment](#3-activate-the-virtual-environment)
  - [4. Install Dependencies](#4-install-dependencies)
  - [5. Deactivate the Virtual Environment](#5-deactivate-the-virtual-environment)
- [License](#license)

## Purpose

This project was created to make the discovery process for a network refresh easy, consistent and comprehensive. The discovery data can be used to create a change request for the customer and will make troubleshooting any issues after a switch is replaced easier.

----------------------------------------------------------------

## The Process

The "procurve-Config-pull.py" script uses the [netmiko](https://github.com/ktbyers/netmiko) library and the Google [textFSM](https://github.com/networktocode/ntc-templates/tree/master) libraries to connect to a switch, run show commands and create JSON files.

Once the data has been collected, there are helper scripts that create:

- port maps
- CDP neighbor tables
- LLDP neighbor tables
- OSPF neighbor tables

A "show run structured" file is created in the "Running" directory. The Procurve firmware allows you to include the "structured" keyword after the "show running" command. This groups the output in an easier to read format.

There is also a text file of "show commands" sent. This file can be edited to send any show commands you need. The filename is procurve-config-file.txt.

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

This output is very functional, you get enough information to build a detailed cutover plan.

The script saves the data to various directories for easy access.

----------------------------------------------------------------

## Deployment questions for Discovery

The script will pull any information that you put into the procurve-config file but it can't answer all the questions! Here are some questions I ask during the kickoff meeting with the customer. This is not a exhaustive list, feel free to add to it.

- What are the labeling requirements
  - Location
  - What information
  - size
  - material
- What are the asset Tag requirements?
- Is an escort required when we are on site?
- What firmware version should be installed?
- Do you have a standard for host names?
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
- snmp requirements
  - Version
  - community names
  - location
  - Required traps
- ssh
  - Host Key type?
  - Ciphers?
  - MACs?
  - key length?
- Power cord connector requirements
  - NEMA 5-15
  - NEMA L5-20
  - NEMA L6-20
  - IEC C14
  - etc

----------------------------------------------------------------

## Getting Started

Follow these steps to set up and run the project:

### 1. Clone the Repository

```bash
git clone https://github.com/rikosintie/Discovery.git
cd Discovery
```

If you don't have git installed, you can download the zip file from the [repository](https://github.com/rikosintie/Discovery). Click on the green "Code" button and select "Download ZIP". Then unzip the file.

<p align="center" width="60%">
<img width="40%" src="https://github.com/rikosintie/Discovery/blob/main/images/GitHub-Code.png" alt="Github ZIP file">
</p>

NOTE: Once you have the repository cloned it is linked to the repository on github.com. You should issue a `git pull` once in a while to pull down any changes that have been made to the repository.

### 2. Create a Virtual Environment

`python -m venv venv --upgrade-deps --prompt="Discovery"`

This will create the standard "venv" directory but when activated will display "Discovery". I prefer this over using `python -m venv Discovery` because it's the standard way to create the virtual environment. But I like seeing Discovery instead of venv when I activate the environment.

The `--upgrade-deps` argument tells python to upgrade pip to the latest version when creating the virtual environment. You need internet access for pip to be upgraded. If you don't have internet access, remove the `--upgrade-deps` argument.

### 3. Activate the Virtual Environment

On Windows

`.\venv\Scripts\activate`

On macOS/Linux

`source venv/bin/activate`

Here is what my terminal looks like after activating:

<p align="center" width="100%">
<img width="100%" src="https://github.com/rikosintie/Discovery/blob/main/images/venv.png" alt="venv">
</p>

### 4. Install Dependencies

You can use `pip list` to list the packages currently installed. If you run it now you will see:

```bash
$ pip list
Package    Version
---------- -------
pip        23.3.2
setuptools 69.0.3
```

Now run the following:

`pip install -r requirements.txt`

You will see all the dependencies being downloaded and installed. Here is a snippet of the dependencies.

```bash
$ pip install -r requirements.txt
Collecting asttokens~=2.4.1 (from -r requirements.txt (line 1))
  Downloading asttokens-2.4.1-py2.py3-none-any.whl.metadata (5.2 kB)
Collecting bcrypt~=4.1.2 (from -r requirements.txt (line 2))
  Downloading bcrypt-4.1.2-cp39-abi3-manylinux_2_28_x86_64.whl.metadata (9.5 kB)
```

Now if we run `pip list` we will see that the dependencies have been installed:

```bash
$ pip list
Package       Version
------------- -------
asttokens     2.4.1
bcrypt        4.1.2
cffi          1.16.0
colorama      0.4.6
cryptography  41.0.7
executing     2.0.1
future        0.18.3
icecream      2.1.3
netmiko       4.3.0
ntc_templates 4.1.0
paramiko      3.4.0
pip           23.3.2
prettytable   3.9.0
pycparser     2.21
Pygments      2.17.2
PyNaCl        1.5.0
pyserial      3.5
PyYAML        6.0.1
scp           0.14.5
setuptools    69.0.3
six           1.16.0
textfsm       1.1.3
wcwidth       0.2.12

```

### 5. Deactivate the Virtual Environment

When you are finished, deactivate the environment

`deactivate`

----------------------------------------------------------------

## License

This project is licensed under the Unlicense - see the LICENSE file for details.
