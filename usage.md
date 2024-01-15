[Home](https://github.com/rikosintie/Discovery/)<!-- omit from toc -->

# Usage<!-- omit from toc -->

- [Before you can run the script](#before-you-can-run-the-script)
- [Create the device inventory file](#create-the-device-inventory-file)
- [Password](#password)
  - [Creating an Environment Variable](#creating-an-environment-variable)
  - [Being prompted for the password](#being-prompted-for-the-password)
  - [Update the mac.txt file](#update-the-mactxt-file)
- [Run the discovery script](#run-the-discovery-script)
- [Failure to connect to a switch](#failure-to-connect-to-a-switch)
- [Building a list of switches](#building-a-list-of-switches)
  - [Review the bootstrap report](#review-the-bootstrap-report)
    - [References](#references)

----------------------------------------------------------------

## Before you can run the script

There are a few steps needed before starting the discovery process:

- Create a device inventory file
- Make changes to the procurve-config-file.txt file (if needed)
- Decide how you want store the password
- Update the mac.txt file to match the format of the switches

----------------------------------------------------------------

## Create the device inventory file

You must create a csv file that contains the following:

`ip_address,hp_procurve,hostname,username`

For example,

`198.51.100.52,hp_procurve,Procurve-2920-24,mhubbard`

Create one line for every switch that you want to process.

You can use either a spreadsheet program or a text editor to create the inventory file but it must have a ".csv" file extension. If you use vscode, there is a plugin called Rainbow csv that allows you to work with csv files in vscode. It also allows you to use SQL syntax to query the file. Very nice if the file gets to be long.

Save the file as `device-inventory-<site name>.csv` in the root of the project folder.

For example,
`device-inventory-HQ.csv`

There is a sample file named device-inventory-area1.csv in the project

## Password

This is always an area of concern. The script supports two methods:

- Create an environment variable "cyberARK" and save the password to the variable.
- include `-p 1` on the command line to be prompted for the password

Neither method is perfect but using either the environment variable or being prompted is more secure than having a csv file with plaintext passwords in it.

### Creating an Environment Variable

On Windows you use control panel to create a "user environment variable". You can follow the instructions [Here](https://www.tenforums.com/tutorials/121664-set-new-user-system-environment-variables-windows.html). I think that you have to log out and log in again to make the environment variable active.

On macOS/Linux

From the terminal that you will run the script in `export cyberARK=Password`. You have to do the export in the terminal that the script will be run in. If you are using vscode and debugging in vscode, that means the vscode terminal.

### Being prompted for the password

This is easier than setting up environment variable. You simply add `-p 1` to the command line.

For example, to run the script for a site named HQ:

`python3 procurve-Config-pull.py -s HQ -p 1`

When you press enter, you will see "Input the Password:" on the command line. Enter the password and press [enter]

----------------------------------------------------------------

### Update the mac.txt file

To create the port maps the mac-address table must be saved but it has to saved by interface.

Since the procurve switches can be stacked and the 5400 series has modules, the port numbers change depending on the model and stacking.

The mac.txt file that is in the project is built for a single 48 port switch. If you are pulling the data from a stack or 5400 series, you have to modify the port numbers in the mac.txt file.

There is a file [procurve-show-mac-interfaces.txt](https://github.com/rikosintie/Discovery/blob/main/procurve-show-mac-interfaces.txt) in the project that has `show mac-address` commands for the 5400 series, individual 2930 switches and stacked switches up to 8.

Simply open the file, copy the interfaces you need and save them into the mac.txt file before running the discovery script.

----------------------------------------------------------------
## Run the discovery script

Now that the project is set up and the inventory file is created, you can run the script.

`python3 procurve-Config-pull.py -s HQ`

Note: you may have to use python instead of python3 depending on your OS.

I recommend running the script on one switch the first time instead of a long list of switches. That will let you see the content of the show commands and make changes if needed before spending time running it on a long list of switches.

The files will be saved in the following directories:

- CR-data - files that are ready for viewing
- Interface - files that need further processing
- Running - The "show running structured" output for each switch

----------------------------------------------------------------

## Failure to connect to a switch

If a switch does not respond or if the the credentials are incorrect, a message will be printed to the console and the script will continue processing the next switch.

It's really disruptive to the discovery process if switches fail. That means you have to fix the problem and then create a new inventory file with just the failed switches, then rerun it.

I recommend saving the switch IP addresses in a plain text file, one per line, and then using nmap to verify that ssh is working.

For example, create a new text file named `ip.txt`. If you are using vs code and the Rainbow csv extension you can simply run a query:

`select a1`

That will return all the IP addresses.

At the bottom of vs code, click `query`.

<p align="center" width="100%">
<img width="60%" src="https://github.com/rikosintie/Discovery/blob/main/images/Rainbow-query.png" alt="Rainbow SQL query">

When the query page opens, enter `select a1` and click `run`.

<p align="center" width="100%">
<img width="60%" src="https://github.com/rikosintie/Discovery/blob/main/images/Rainbow-parameters.png" alt="Select Query">
</p>

The query will return a list of IP addresses, 1 per line.

```bash
192.168.10.50
192.168.10.52
192.168.10.111
192.168.10.230
```

And run nmap with these arguments:

`nmap -v -p 22 -iL ip.txt --reason -oN ip-dead.txt`

This tells nmap to use ip.txt for the target IP addresses, include the reason and save the output to ip-dead.txt.

In this example only 3 devices are working:

`Nmap done at Sun Jan  7 20:05:46 2024 -- 4 IP addresses (3 hosts up) scanned`

If you don't get 100% you can open `ip-dead.txt` and search for "down".

There isn't a simple way to verify that the credentials will work. If you have permission to run the nmap ssh-brute script you can verify using:

`nmap -p 22 --script ssh-brute --script-args userdb=user.lst,passdb=pass.lst -iL ip.txt`

Put your username in user.lst and your password in pass.lst.

You will get back a report for each device:

```bash
Nmap scan report for 192.168.10.52
Host is up (0.0033s latency).

PORT   STATE SERVICE
22/tcp open  ssh
| ssh-brute:
|   Accounts:
|     vector:H3lpd3sk - Valid credentials
|_  Statistics: Performed 2 guesses in 2 seconds, average tps: 1.0

Nmap scan report for 192.168.10.111
Host is up (0.0028s latency).

PORT   STATE SERVICE
22/tcp open  ssh
| ssh-brute:
|   Accounts: No valid accounts found
|_  Statistics: Performed 2 guesses in 4 seconds, average tps: 0.5
```

Then use `grep -Eir -b6 "No valid" accounts.txt` to find the devices with no valid accounts.

**Grep Arguments:**

- E - extended
- i - case-insensitive
- r - recursive
- -b6 - show 6 lines before the match

----------------------------------------------------------------

## Building a list of switches

Not all customers will have a clean list of switch IP addresses and host names. If there is a management network you may be able to look at the arp table and pull out the switches. As a last resort you can use the following process to build a list of switches.

Run this nmap command to find devices with ssh and snmp open. Most devices that have ssh and snmp open are switches. You may have to do some additional filtering.

`sudo nmap -sU -sT -T4 -sC -p U:161,T:22 -oA procurve-scan -n -Pn --open --stylesheet https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl  <target ips>`

Note: the stylesheet is from [honze-net-nmap-bootstrap-xsl](https://github.com/honze-net/nmap-bootstrap-xsl). This is a repository for creating nmap reports. Well worth a look.

The `-oA procurve` switch will create the following files:

- procurve-scan.xml - a standard XML format file
- procurve-scan.nmap - an nmap format file
- procurve-scan.gnmap - a greppable nmap format file

but they will be owned by the root account since we used `sudo` because of the UDP scan. Here are the permissions:

```bash
$ ls -l procurve-scan*
-rw-r--r-- 1 root root  477 2024-01-14 17:13 procurve-scan.gnmap
-rw-r--r-- 1 root root  926 2024-01-14 17:13 procurve-scan.nmap
-rw-r--r-- 1 root root 3.6K 2024-01-14 17:13 procurve-scan.xml
```

Run the following to take ownership of the files:

`sudo chown $USER procurve-scan*`

The results:

```bash
ls -l procurve-scan*
-rw-r--r-- 1 mhubbard root  477 2024-01-14 17:13 procurve-scan.gnmap
-rw-r--r-- 1 mhubbard root  926 2024-01-14 17:13 procurve-scan.nmap
-rw-r--r-- 1 mhubbard root 3.6K 2024-01-14 17:13 procurve-scan.xml
```

The output will look something like this:

```bash
sudo nmap -sU -sT -T4 -sC -p U:161,T:22 -oA procurve-scan -n -Pn --open --stylesheet [nmap-bootstrap.xsl](https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl) 192.168.10.52
Host discovery disabled (-Pn). All addresses will be marked 'up' and scan times will be slower.
Starting Nmap 7.91 ( https://nmap.org ) at 2024-01-14 17:09 PST
Nmap scan report for 192.168.10.52
Host is up (0.0032s latency).

PORT    STATE         SERVICE
22/tcp  open          ssh
| ssh-hostkey:
|_  1024 cb:a8:d6:c7:da:bd:67:53:91:8c:c0:1b:49:d1:a1:2d (DSA)
| ssh-os:
|_  SSH Banner: SSH-2.0-Mocana SSH 6.3\x0D
161/udp open|filtered snmp
| snmp-info:
|   enterprise: Hewlett-Packard
|   engineIDFormat: unknown
|   engineIDData: 000098f2b3fe8880
|   snmpEngineBoots: 108
|_  snmpEngineTime: 5h40m26s
MAC Address: 98:F2:B3:FE:88:80 (Hewlett Packard Enterprise)

Host script results:
|_smbv2-enabled: ERROR: Script execution failed (use -d to debug)

Nmap done: 1 IP address (1 host up) scanned in 15.03 seconds
```

Let's look at the contents of the procurve-scan.gnmap file:

```bash
# Nmap 7.91 scan initiated Sun Jan 14 17:13:39 2024 as: nmap -sU -sT -T4 -sC -p U:161,T:22 -oA procurve-scan -n -Pn --open --stylesheet https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl 192.168.10.52
Host: 192.168.10.52 ()  Status: Up
Host: 192.168.10.52 ()  Ports: 22/open/tcp//ssh///, 161/open|filtered/udp//snmp//Hewlett-Packard SNMPv3 server/
# Nmap done at Sun Jan 14 17:13:54 2024 -- 1 IP address (1 host up) scanned in 15.09 seconds
```

 We can use this to find the switches in the procurve.gnmap file. Using the following grep/awk command:

 ```bash
 grep -Eir  "22/open/tcp//ssh///, 161/open|filtered/udp//snmp//" procurve.gnmap | awk '{ print $2 }'
192.168.10.52
 ```

The `grep` found just the ssh, snmp string and `awk` printed the data in column 2.

### Review the bootstrap report

The "stylesheet" argument creates an xsl file to format the XML file that the script creates. You will be able to right-click on the xml file and open it in Firefox so see a nicely formatted report. That isn't required, it's just nice. Here is a simple example from my home lab:

<p align="center" width="100%">
<img width="60%" src="https://github.com/rikosintie/Discovery/blob/main/images/nmap-bootstarp-stylesheet.png" alt="nmap-report">
</p>

If you want to open it in a Chromium browser you will need to do the following:

- Open this [page](https://www.freeformatter.com/xsl-transformer.html#before-output) in Chrome/Edge
- Paste the text from procurve.xml into "Option 1: Copy-paste your XML document here"
- Open nmap-bootstrap-xsl in a text editor and on line 8, delete -  `doctype-system="about:legacy-compat"`
- Paste the text into "Option 2: Option 1: Copy-paste your XSL document here"
- click `Transform XML`
- Save the new text as procurve.html. You lose a little bit of the report but it's still usable.


If you are on Mac/Linux or Windows WSL you can use grep to pull out a list of the switches.

#### References

XSL Transformer - XSLT
- [Restrictions on File Urls](https://textslashplain.com/2019/10/09/navigating-to-file-urls/)
- [Transform XML+XSLT to plain html so that it loads without blocking](https://gist.github.com/ericlaw1979/deb716d8436890420c41c8a593bfd509)
- [Enabling Internet Explorer Mode in Microsoft Edge](https://csuf-erp.screenstepslive.com/m/70023/l/1650548-enabling-internet-explorer-mode-in-microsoft-edge)
- [nmap-bootstrap-xsl](https://github.com/honze-net/nmap-bootstrap-xsl)


[Home](https://github.com/rikosintie/Discovery/)<!-- omit from toc -->
