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

`show vlan custom id name:20 ipaddr state`

The data is saved to various directories for easy access.

----------------------------------------------------------------

## Getting Started

Follow these steps to set up and run the project:

### 1. Clone the Repository

```bash
git clone https://github.com/rikosintie/Discovery.git
cd Discovery
```

If you don't have git installed, you can download the zip file from the [repository](https://github.com/rikosintie/Discovery). Click on the green "Code" button and select "Download ZIP". Then unzip the file.

<p align="center" width="100%">
<img width="60%" src="https://github.com/rikosintie/Discovery/blob/main/images/GitHub-Code.png" alt="Github ZIP file">
</p>

### 2. Create a Virtual Environment

`python -m venv venv --upgrade-deps --prompt="Discovery"`

This will create the standard "venv" directory but when activated will display "Discovery". I prefer this over using `python -m venv Discovery` because it's the standard way to create the virtual environment. But I like seeing Discovery instead of venv when I activate the environment.

The `--upgrade-deps` argument tells python to upgrade pip to the latest version while creating the virtual environment. You need internet access for pip to be upgraded. If you don't have internet access, remove the `--upgrade-deps` argument.

### 3. Activate the Virtual Environment

On Windows

`.\venv\Scripts\activate`

On macOS/Linux

`source venv/bin/activate`

### 4. Install Dependencies

`python setup.py install`

### 6. Deactivate the Virtual Environment

When you are finished, deactivate the environment

`deactivate`

## Usage

### Create the device inventory file

You must create a csv file that contains the following:

`ip_address,hp_procurve,hostname`

For example,

`198.51.100.52,hp_procurve,Procurve-2920-24`

Create one line for every switch that you want to process.

Save the file as `device-inventory-<site name>.csv` in the root of the project folder.

For example,
`device-inventory-hq.csv`

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

The "#" symbols is the comment command in python. Any line starting with a "#" will be ignored.

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
