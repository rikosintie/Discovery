# The Helper Scripts<!-- omit from toc -->

After the `procurve-Config-pull.py` script finishes, you can use the ***hostname-CR-data.txt*** files to get started planning. But the script also creates JSON files for cdp neighbors, lldp neighbors and OSPF neighbors.

In the "Interface" folder

- hostname-cdp.txt - JSON format of the "show cdp ne det" command
- hostname-lldp.txt - JSON format of "show lldp info rem det" command

This section will discuss the scripts that convert the JSON into reports.

## Reviewing CDP Neighbors

The Procurve switches support cisco discovery protocol (cdp) even though it's a Cisco proprietary protocol. By default it's not running. If you want to use cdp you have to enable it.

```bash
config t
HP-2920-24G-PoEP(config)# cdp run
```

Optionally you can enable cdp on only certain ports. For example,

```bash
HP-2920-24G-PoEP(config)# cdp enable ?
[ethernet] PORT-LIST  Enter a port number, a list of ports or 'all' for all ports.
```

There is an argument that having CDP enabled on all ports is a security risk. You have to decide for yourself if the risk is worth the visibility of running CDP. Personally, my feeing is that if an attacker has unfettered access to your swtiches the game is already over so I enable it.

The exception is for ports that connect to external entities such as an ISP or extranet partner.

To view the list of ports that have cdp enabled:

```bash
sh cdp

 Global CDP information

  Enable CDP [Yes] : Yes
  CDP mode [rxonly] : rxonly


  Port   CDP
  ------ --------
  1      enabled
  2      enabled
  3      enabled
```
To view all the cdp options, from configuration mode, you can use

```bash
cdp ?
 enable                Enable CDP on particular device ports.
 mode                  Set various modes of CDP (Cisco Discovery Protocol) processing.
 run                   Start CDP on the device.
 ```

### The cdp scripts

 There are two scripts for CDP neighbors.

- procurve-cdp-ne-report.py - This script creates a text file for the cdp neighbors
- procurve-cdp-ne-csv.py - This script creates a CSV file for the cdp neighbors

I wrote the script that creates the csv file so that you could use a spreadsheet or the Rainbow csv extension to sort the data.

Each of these scripts uses the same device-inventory file as the procurve-Config-pull.py script so there is no configuration needed. Just use:

- `python3 procurve-cdp-ne-report.py -s sitename`
- `python3 procurve-cdp-ne-csv.py -s sitename`

The reports are saved into the "Interface\neighbors" directory.

### The cdp neighbor text report

Here is a snippet of the cdp neighbor text report:

```bash
------------------------------
destination_host: 3750x.pu.pri
   management_ip: 192.168.1.1
        platform: cisco WS-C3750X-48P
     remote_port: GigabitEthernet1/1/2
      local_port: 21
software_version: Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-...
```

Here is a screenshot of the csv report in vs code using the Rainbow csv extension:

<p align="left" width="100%">
<img width="60%" src="https://github.com/rikosintie/Discovery/blob/main/images/csv-snippet.png" alt="CSV format">
</p>

## Reviewing LLDP neighbors

```bash
sh lldp config

 LLDP Global Configuration

  LLDP Enabled [Yes] : Yes
  LLDP Transmit Interval    [30] : 30
  LLDP Hold time Multiplier  [4] : 4
  LLDP Reinit Interval       [2] : 2
  LLDP Notification Interval [5] : 5
  LLDP Fast Start Count      [5] : 5


 LLDP Port Configuration

  Port  | AdminStatus NotificationEnabled Med Topology Trap Enabled
  ----- + ----------- ------------------- -------------------------
  1     | Tx_Rx       False               False
  2     | Tx_Rx       False               False
```
