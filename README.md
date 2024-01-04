# HPE Procurve Discovery Project<!-- omit from toc -->

## Purpose

This project was created to make the discovery process for a network refresh easy, consistent and comprehensive. The discovery data can be used to create a change request for the customer and will make troubleshooting any issues after a switch is replaced easier.

----------------------------------------------------------------

## The Process

The "procurve-Config-pull.py" script uses the [netmiko](https://github.com/ktbyers/netmiko) library and the Google [textFSM](https://github.com/networktocode/ntc-templates/tree/master) libraries to connect to a switch, run show commands and create JSON files.

Once the data has been collected, there are helper scripts that create port maps, CDP neighbor tables, LLDP neighbor tables, OSPF neighbor tables, etc.

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
This output is very functional, you get

The script saves the data to various directories for easy access.

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

You can use `pip list` to list the dependencies. If you run it now you will see:

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

## Usage

There are a few steps needed to be ready to do the discovery process:

- Create a device inventory file
- Decide how you want store the password
- Update the mac.txt file to match the format of the switches

### Create the device inventory file

You must create a csv file that contains the following:

`ip_address,hp_procurve,hostname`

For example,

`198.51.100.52,hp_procurve,Procurve-2920-24`

Create one line for every switch that you want to process.

Save the file as `device-inventory-<site name>.csv` in the root of the project folder.

For example,
`device-inventory-hq.csv`

There is a sample file named device-inventory-area1.csv in the project

### Password

This is always an area of contention. You can create an environment variable cyberARK and save the password to the variable.

On Windows you use control panel to create a user environment variable. I'm not a windows user but you can follow the instructions [Here](https://www.tenforums.com/tutorials/121664-set-new-user-system-environment-variables-windows.html)

I think that you have to log out and log in again to make the environment variable active.

On macOS/Linux
From the terminal that you will run the script in `export cyberARK=Password`

### Use the device-inventory file

You can also add the password to the device-inventory file using

`198.51.100.52,hp_procurve,Procurve-2920-24,Sup#rS3cr3t`

If you chose to put the password in the csv file you must make a change to the script. Locate the following code

```bash
# password = line.split(",")[4]
password = os.environ.get("cyberARK")
```

And change it to

```python
    password = line.split(",")[4]
    # password = os.environ.get("cyberARK")
```

The "#" symbol is the comment command in python. Any line starting with a "#" will be ignored.

Now that the project is set up and the inventory file is created, you can run the script.

`python3 procurve-Config-pull.py`

Note: you may have to use python instead of python3 depending on your OS.

I recommend running the script on one switch the first time instead of a long list of switches. That will let you see the content of the show commands and make changes if needed before spending time running it on a long list of switches.

The files will be saved in the following directories:

- CR-data - files that are ready for viewing
- Interface - files that need further processing
- Running - The "show running structured" output for each switch

## License

This project is licensed under the Unlicense - see the LICENSE file for details.
