[Home](https://github.com/rikosintie/Discovery/)<!-- omit from toc -->

# Usage<!-- omit from toc -->

- [Before you can run the script](#before-you-can-run-the-script)
- [Create the device inventory file](#create-the-device-inventory-file)
- [Password](#password)
  - [Creating an Environment Variable](#creating-an-environment-variable)
  - [Being prompted for the password](#being-prompted-for-the-password)
- [Update the mac.txt file](#update-the-mactxt-file)
- [Update the procurve-config-file.txt file](#update-the-procurve-config-filetxt-file)
- [Run the discovery script](#run-the-discovery-script)
  - [What options are available](#what-options-are-available)
  - [What do the arguments do](#what-do-the-arguments-do)
    - [Collecting switch logs](#collecting-switch-logs)
    - [Setting the Password](#setting-the-password)
    - [SSH Logging](#ssh-logging)
    - [Timeout](#timeout)
  - [Examples](#examples)
- [Failure to connect to a switch](#failure-to-connect-to-a-switch)
  - [Use nmap to verify switches are up](#use-nmap-to-verify-switches-are-up)
  - [Use nmap to verify the credentials](#use-nmap-to-verify-the-credentials)
- [Building a list of switches](#building-a-list-of-switches)
  - [Review the bootstrap report](#review-the-bootstrap-report)
  - [Opening the report in a Chromium based browser](#opening-the-report-in-a-chromium-based-browser)
  - [An alternative way to view the report in a Chromium browser](#an-alternative-way-to-view-the-report-in-a-chromium-browser)
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

## Update the mac.txt file

To create the port maps the mac-address table must be saved but it has to saved by interface.

Since the procurve switches can be stacked and the 5400 series has modules, the port numbers change depending on the model and stacking.

The mac.txt file that is in the project is built for a single 48 port switch. If you are pulling the data from a stack or 5400 series, you have to modify the port numbers in the mac.txt file.

There is a file [procurve-show-mac-interfaces.txt](https://github.com/rikosintie/Discovery/blob/main/procurve-show-mac-interfaces.txt) in the project that has `show mac-address` commands for the 5400 series, individual 2930 switches and stacked switches up to 8.

Simply open the file, copy the interfaces you need and save them into the mac.txt file before running the discovery script.

----------------------------------------------------------------

## Update the procurve-config-file.txt file

This file contains all of the `show commands` that will be sent to the switches. It has fifty commands in it including many that may not apply to customer:

- show lacp peer
- show lacp local
- show lacp mad-passthrough
- show dhcp-server binding
- show dhcp-server pool

If you don't need them for a particular customer you can just open the file and delete any that you don't need.

For pulling the mac-address table, which most customers want you to do, I have an include statement using a regex. In the sample file it doesn't pull mac addresses for ports on modules A and B. These were uplinks on the switch that I tested the script on.

`show show mac-address | ex "A|B"`

If you are running the scrip against a 1U switch or your 5400 series uplinks are different, change the regex to meet your needs.

----------------------------------------------------------------

## Run the discovery script

Now that the project is set up and the inventory file is created, you can run the script. Make sure you are in the Discovery directory and run:

```bash
~/Discovery on  main
$ source bin/activate
```

To activate the the virtual environment.

### What options are available

You can run the script with -h to get help:

```bash
python3 procurve_Config_pull.py -h


usage: procurve_Config_pull.py [-h] [-e EVENT] [-l LOGGING] [-p PASSWORD] [-s SITE] [-t TIMEOUT]

-s site, -l 1 create log.txt, -p 1 prompt for password, -t 1-9 timeout, -e W,I,M,D,E to pull logs

options:
  -h, --help            show this help message and exit
  -e EVENT, --event EVENT
                        -e W,I,M,D,E to pull switch logs
  -l LOGGING, --logging LOGGING
                        use -l 1 to enable ssh logging
  -p PASSWORD, --password PASSWORD
                        use -p 1 to be prompted for password
  -s SITE, --site SITE  Site name - ex. HQ
  -t TIMEOUT, --timeout TIMEOUT
                        use -t 1-9 to set timeout
(Discovery)
```

### What do the arguments do

The only required argument is `-s site`. This references the device-inventory file.

#### Collecting switch logs

The procurve switches allow you to pull five different types of logs:

- Warning (W) - This log contains warning messages
- Informational (I) - This log can grow very large and may need a large timeout value. If you have a lot of switches to discovery and they have large informational logs you may want to skip them.
- Major (M) - This log contains major messages
- Debug (D) - This log contains debug messages
- Error (E) - This log contains error messages

If you want to pull logs from the switch add `-e` and the type of log. You can collect 1 or all 5. Separate the values with a comma. For example:

`-e W,I,M,D,E`

#### Setting the Password

If you want to be prompted for a password add `-p 1`. If you don't use -p 1 you must set an environment variable cyberARK with the password. That is covered above in the "[password](#password)" section.

#### SSH Logging

If you want to enable ssh logging add `-l 1`. You would do that to troubleshoot if you are getting "time out" errors.

#### Timeout

You can modify the timeout value using  `-t`. Note: the number sets the timeout value in 100s of seconds. If you use `-t 2` it will wait up to 200 seconds for the operation to complete.

### Examples

The minimum is to use -s for the site:

`python3 procurve-Config-pull.py -s HQ`

To include the Warning log:

`python3 procurve-Config-pull.py -s HQ -e W`

To include all logs and set timeout to 2:

`python3 procurve-Config-pull.py -s HQ -e W,I,M,D,E -t 2`

To be prompted for a password:

`python3 procurve-Config-pull.py -s HQ -p 1`

Note: you may have to use python instead of python3 depending on your OS.

I recommend running the script on one switch the first time instead of a long list of switches. That will let you see the content of the show commands and make changes if needed before spending time running it on a long list of switches.

The files will be saved in the following directories:

- CR-data - files that are ready for viewing
- Interface - files that need further processing
- Running - The "show running structured" output for each switch

If you are having timeout or authentication issues, enable logging. Here is a sample output of the log.txt file that netmiko creates:

```bash
DEBUG:paramiko.transport:starting thread (client mode): 0xb4b346d0
DEBUG:paramiko.transport:Local version/idstring: SSH-2.0-paramiko_3.4.0
DEBUG:paramiko.transport:Remote version/idstring: SSH-2.0-Mocana SSH 6.3
INFO:paramiko.transport:Connected (version 2.0, client Mocana)
DEBUG:paramiko.transport:=== Key exchange possibilities ===
DEBUG:paramiko.transport:kex algos: ecdh-sha2-nistp256, ecdh-sha2-nistp384, ecdh-sha2-nistp521, diffie-hellman-group-exchange-sha256, diffie-hellman-group14-sha1
DEBUG:paramiko.transport:server key: rsa-sha2-512, rsa-sha2-256, ssh-rsa
DEBUG:paramiko.transport:client encrypt: aes256-ctr, rijndael-cbc@lysator.liu.se, aes192-ctr, aes128-ctr
DEBUG:paramiko.transport:server encrypt: aes256-ctr, rijndael-cbc@lysator.liu.se, aes192-ctr, aes128-ctr
DEBUG:paramiko.transport:client mac: hmac-sha1-96, hmac-sha1
DEBUG:paramiko.transport:server mac: hmac-sha1-96, hmac-sha1
DEBUG:paramiko.transport:client compress: none
DEBUG:paramiko.transport:server compress: none
DEBUG:paramiko.transport:client lang: <none>
DEBUG:paramiko.transport:server lang: <none>
DEBUG:paramiko.transport:kex follows: False
DEBUG:paramiko.transport:=== Key exchange agreements ===
DEBUG:paramiko.transport:Kex: ecdh-sha2-nistp256
DEBUG:paramiko.transport:HostKey: rsa-sha2-512
DEBUG:paramiko.transport:Cipher: aes128-ctr
DEBUG:paramiko.transport:MAC: hmac-sha1
DEBUG:paramiko.transport:Compression: none
DEBUG:paramiko.transport:=== End of kex handshake ===
DEBUG:paramiko.transport:kex engine KexNistp256 specified hash_algo <built-in function openssl_sha256>
DEBUG:paramiko.transport:Switch to new keys ...
DEBUG:paramiko.transport:Adding ssh-rsa host key for 10.112.254.60: b'47708eeea6cbecf20b5916d675feca3d'
DEBUG:paramiko.transport:userauth is OK
INFO:paramiko.transport:Auth banner: b'******************************************************************************\nThis system is the property of Rim of the World Unified School District.\n\nUNAUTHORIZED ACCESS TO THIS DEVICE IS PROHIBITED.\n\nYou must have explicit permission to access this device.\n\nAll activities performend on this device are logged.\nAny violations of access policy will result in disciplinary action.\n****************************************************************************** \n\n'
INFO:paramiko.transport:Authentication (password) successful!
```

Here is a sample output from running the script:

```bash
procurve_Config_pull.py -s area1 -e W


-------------------------------------------------
Reading devices from: device-inventory-area1.csv
----------------------------------------------------------
01/21/2024, 19:02:50 Connecting to switch Procurve-2920-24
----------------------------------------------------------

Exec time: 0:00:01.279461

Could not connect to Procurve-2920-24 at 192.168.10.50. The Credentials failed.  Remove it from the device inventory file
----------------------------------------------------------
01/21/2024, 19:02:51 Connecting to switch Procurve-2920-48
----------------------------------------------------------

HP-2920-24G-PoEP#

--------------------------------------------------------
processing procurve-config-file.txt for Procurve-2920-48
--------------------------------------------------------
processing show logging -W for Procurve-2920-48
--------------------------------------------------------
Writing show logging -W commands to /home/mhubbard/04_Tools/Discovery/CR-data/Procurve-2920-48-log-W.txt
--------------------------------------------------------
collecting show interface for Procurve-2920-48
--------------------------------------------------------
collecting show system for Procurve-2920-48
--------------------------------------------------------
collecting show cdp detail for Procurve-2920-48
--------------------------------------------------------
collecting show interfaces brief for Procurve-2920-48
--------------------------------------------------------
collecting show lldp neighbors for Procurve-2920-48
--------------------------------------------------------
collecting show mac address for Procurve-2920-48
--------------------------------------------------------
collecting show arp for Procurve-2920-48
--------------------------------------------------------
Collecting show running-config from Procurve-2920-48
--------------------------------------------------------
Writing show commands to /home/mhubbard/04_Tools/Discovery/CR-data/Procurve-2920-48-CR-data.txt
-------------------------------------------------
Writing MAC addresses to /home/mhubbard/04_Tools/Discovery/port-maps/data/Procurve-2920-48-mac-address.txt
-------------------------------------------------
Writing ARP data to /home/mhubbard/04_Tools/Discovery/port-maps/data/Procurve-2920-48-arp.txt
-------------------------------------------------
Writing show run to /home/mhubbard/04_Tools/Discovery/port-maps/data/Procurve-2920-48-arp.txt
-------------------------------------------------
Writing interfaces json data to /home/mhubbard/04_Tools/Discovery/Interface/Procurve-2920-48-system.txt
-------------------------------------------------
Writing interfaces json data to /home/mhubbard/04_Tools/Discovery/Interface/Procurve-2920-48-interface.txt
-------------------------------------------------
Writing interfaces brief data to /home/mhubbard/04_Tools/Discovery/Interface/Procurve-2920-48-int_br.txt
-------------------------------------------------
Writing cdp neighbor data to /home/mhubbard/04_Tools/Discovery/Interface/Procurve-2920-48-cdp.txt
-------------------------------------------------
Writing show lldp data to /home/mhubbard/04_Tools/Discovery/Interface/Procurve-2920-48-lldp.txt

-------------------------------------------------------
Successfully created config files for Procurve-2920-48
-------------------------------------------------------

Data collection is complete.
Total running time: 0.0 Hours 1.0 Minutes 44.67 Seconds
```

----------------------------------------------------------------

## Failure to connect to a switch

If a switch does not respond or if the the credentials are incorrect, a message will be printed to the console and the script will continue processing the next switch.

It's really disruptive to the discovery process if switches fail. That means you have to fix the problem and then create a new inventory file with just the failed switches, then rerun it.

### Use nmap to verify switches are up

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

### Use nmap to verify the credentials

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

Run this nmap command to find devices with ssh **and** snmp open. Most devices that have ssh and snmp open are switches. You may have to do some additional filtering.

`sudo nmap -sU -sS -T4 -sC -p U:161,T:22 -oA procurve-scan -n -Pn --open --stylesheet https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl  <target ips>`

Note: the stylesheet is from [honze-net-nmap-bootstrap-xsl](https://github.com/honze-net/nmap-bootstrap-xsl). This is a repository for creating nmap reports. Well worth a look.

The `-oA procurve-scan` argument will create the following files:

- procurve-scan.xml - a standard XML file with the xsl link embedded
- procurve-scan.nmap - an nmap format file
- procurve-scan.gnmap - a greppable nmap format file

The files will be owned by the root account since we need `sudo` for the UDP scan. Here are the permissions:

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
sudo nmap -sU -sS -T4 -sC -p U:161,T:22 -oA procurve-scan -n -Pn --open --stylesheet [nmap-bootstrap.xsl](https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl) 192.168.10.52
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

The "SSH Banner: SSH-2.0-Mocana SSH 6.3" is the ssh server that is running on the procurve switch. Over the years HPE has used different ssh servers but this banner will help identify procurve switches.

Let's look at the contents of the procurve-scan.gnmap file:

```bash
# Nmap 7.91 scan initiated Sun Jan 14 17:13:39 2024 as: nmap -sU -sS -T4 -sC -p U:161,T:22 -oA procurve-scan -n -Pn --open --stylesheet https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl 192.168.10.52
Host: 192.168.10.52 ()  Status: Up
Host: 192.168.10.52 ()  Ports: 22/open/tcp//ssh///, 161/open|filtered/udp//snmp//Hewlett-Packard SNMPv3 server/
# Nmap done at Sun Jan 14 17:13:54 2024 -- 1 IP address (1 host up) scanned in 15.09 seconds
```

If you are on Mac/Linux/Windows WSL or have git bash (or MobaXterm) installed on Windows you can use grep to pull out a list of the switches from procurve-scan.gnmap file. Use the following grep/awk command:

 ```bash
 grep -Eir  "22/open/tcp//ssh///, 161/open|filtered/udp//snmp//" procurve.gnmap | awk '{ print $2 }'
192.168.10.52
 ```

The `grep` found just the "ssh, snmp" string and `awk` printed the data in column 2.

### Review the bootstrap report

The "stylesheet" argument creates an xsl file to format the XML file that the script creates. You will be able to right-click on the xml file and open it in Firefox to see a nicely formatted report. This isn't required, it's just nice extra and you can give it the customer as documentation. Here is a simple example from my home lab:

<p align="center" width="100%">
<img width="60%" src="https://github.com/rikosintie/Discovery/blob/main/images/nmap-bootstarp-stylesheet.png" alt="nmap-report">
</p>

### Opening the report in a Chromium based browser

If you want to open the report in a Chromium browser you will need to do the following:

- Open this [page](https://www.freeformatter.com/xsl-transformer.html#before-output) in Chrome/Edge
- Paste the text from procurve-scan.xml into "Option 1: Copy-paste your XML document here"
- Open nmap-bootstrap-xsl in a text editor and on line 8, delete -  `doctype-system="about:legacy-compat"`
- Paste the text into "Option 2: Option 1: Copy-paste your XSL document here"
- click `Transform XML`
- Save the new text as procurve-scan.html. You lose a little bit of the report but it's still usable.

### An alternative way to view the report in a Chromium browser

The URL restriction occurs because the xsl file comes from an https server (github) and the file is on disk. If you use "settings, Developer tools, console", you will see this message:

```bash
procurve-scan.xml:3  Unsafe attempt to load URL
https://raw.githubusercontent.com/honze-net/nmap-bootstrap-xsl/master/nmap-bootstrap.xsl
from frame with URL
file:///home/mhubbard/04_Tools/Discovery/procurve-scan.xml.
'file:' URLs are treated as unique security origins.
```

You can use the xsl file that comes from cloning the repository. The drawback to this is that if you want to share the report, you have to include the xsl file.

Change the nmap command to:

```bash
nmap -sU -sS -T4 -sC -p U:161,T:22 -oA procurve-scan -n -Pn --open --stylesheet nmap-bootstrap.xsl 192.168.10.52
```

Now spin up an http server using python:

`python3 -m http.server 8000`

Open a Chromium based browser and enter:

`http://localhost:8000/procurve-scan.xml`

The report will open and not be a limited version.

Learning to use the python http server is a good skill. For example, if you have Aruba APs running in IAP mode and there are a mix of models you have to use http to upgrade them. This method works great on a laptop.

#### References

- [XSL Transformer - XSLT](https://www.freeformatter.com/xsl-transformer.html#before-output)
- [Restrictions on File Urls](https://textslashplain.com/2019/10/09/navigating-to-file-urls/)
- [Transform XML+XSLT to plain html so that it loads without blocking](https://gist.github.com/ericlaw1979/deb716d8436890420c41c8a593bfd509)
- [Enabling Internet Explorer Mode in Microsoft Edge](https://csuf-erp.screenstepslive.com/m/70023/l/1650548-enabling-internet-explorer-mode-in-microsoft-edge)
- [nmap-bootstrap-xsl](https://github.com/honze-net/nmap-bootstrap-xsl)

----------------------------------------------------------------

[Home - ](https://github.com/rikosintie/Discovery/)<!-- omit from toc -->
[Getting Started - ](https://github.com/rikosintie/Discovery/blob/main/Getting_Started.md)
[The Helper Scripts](https://github.com/rikosintie/Discovery/blob/main/Helper-scripts.md)<!-- omit from toc -->
