# Usage<!-- omit from toc -->

There are a few steps needed before starting the discovery process:

- Create a device inventory file
- Make changes to the procurve-config-file.txt file
- Decide how you want store the password
- Update the mac.txt file to match the format of the switches

----------------------------------------------------------------

## Create the device inventory file

You must create a csv file that contains the following:

`ip_address,hp_procurve,hostname`

For example,

`198.51.100.52,hp_procurve,Procurve-2920-24`

Create one line for every switch that you want to process.

You can use either a spreadsheet program or a text editor to create the inventory file but it must have a ".csv" file extension. If you use vscode, there is a plugin called Rainbow csv that allows you to work with csv files right in vscode. It also allows you to use SQL syntax to query the file. Very nice if you file get to be long.

Save the file as `device-inventory-<site name>.csv` in the root of the project folder.

For example,
`device-inventory-hq.csv`

There is a sample file named device-inventory-area1.csv in the project

## Password

This is always an area of contention. The scrip supports two method:

- Create an environment variable "cyberARK" and save the password to the variable.
- Include the password in the inventory file.

### Creating an Environment Variable

On Windows you use control panel to create a "user environment variable". You can follow the instructions [Here](https://www.tenforums.com/tutorials/121664-set-new-user-system-environment-variables-windows.html). I think that you have to log out and log in again to make the environment variable active.

On macOS/Linux

From the terminal that you will run the script in `export cyberARK=Password`. You have to do the export in the terminal that the script will be run in. If you are using vscode and debugging in vscode, that means the vscode terminal.

### Use the device-inventory file

You can also add the password to the device-inventory file using

`198.51.100.52,hp_procurve,Procurve-2920-24,Sup#rS3cr3t`

If you chose to put the password in the csv file keep in mind that the password is in plain text!

Now that the project is set up and the inventory file is created, you can run the script.

`python3 procurve-Config-pull.py`

Note: you may have to use python instead of python3 depending on your OS.

I recommend running the script on one switch the first time instead of a long list of switches. That will let you see the content of the show commands and make changes if needed before spending time running it on a long list of switches.

The files will be saved in the following directories:

- CR-data - files that are ready for viewing
- Interface - files that need further processing
- Running - The "show running structured" output for each switch
