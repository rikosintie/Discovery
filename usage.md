# Usage<!-- omit from toc -->

- [Before you can run the script](#before-you-can-run-the-script)
- [Create the device inventory file](#create-the-device-inventory-file)
- [Password](#password)
  - [Creating an Environment Variable](#creating-an-environment-variable)
  - [Being prompted for the password](#being-prompted-for-the-password)
- [Failure to connect to a switch](#failure-to-connect-to-a-switch)

----------------------------------------------------------------

## Before you can run the script

There are a few steps needed before starting the discovery process:

- Create a device inventory file
- Make changes to tShe procurve-config-file.txt file
- Decide how you want store the password
- Update the mac.txt file to match the format of the switches

----------------------------------------------------------------

## Create the device inventory file

You must create a csv file that contains the following:

`ip_address,hp_procurve,hostname`

For example,

`198.51.100.52,hp_procurve,Procurve-2920-24`

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

This is easier than setting up environment variable. You simple add `-p 1` to the command line.

For example, to run the script for a site named HQ:

`python3 procurve-Config-pull.py -s HQ -p 1`

When you press enter, you will see "Input the Password:" on the command line. Enter the password and press [enter]

----------------------------------------------------------------

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

If a does not respond or if the the credentials are incorrect, a message will be printed to the console and script will continue processing the next switch.

It's really disruptive to the discovery process if switches fail. That means you have to fix the problem and then create a new inventory file, then rerun it.

I recommend saving the switch IP addresses in a plain text file, one per line, and then using nmap to verify that ssh is working.

For example, create a new text file ip.txt:

```bash
192.168.10.50
192.168.10.52
192.168.10.111
192.168.10.230
```

And run nmap with these arguments:

`nmap -v -p 22 -iL ip.txt --reason -oN ip-dead.txt`

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

- E extended
- i case-insensitive
- r recursive
- -b6 show 6 lines before the match
