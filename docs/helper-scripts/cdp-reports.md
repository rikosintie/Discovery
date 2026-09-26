# CDP Neighbor Reports

The Procurve switches support the Cisco discovery protocol (cdp) even though it's a Cisco proprietary protocol. By default it's not running. If you want to use cdp you have to enable it.

```bash
HP-2920-24G-PoEP# config t
HP-2920-24G-PoEP(config)# cdp run
```

Optionally you can enable cdp on only certain ports. For example,

```bash
HP-2920-24G-PoEP(config)# cdp enable ?
[ethernet] PORT-LIST  Enter a port number, a list of ports or 'all' for all ports.
```

There is an argument that having CDP enabled on all ports is a security risk. You have to decide for yourself if the risk is worth the visibility of running CDP. Personally, my feeing is that if an attacker has unfettered access to your switches the game is already over so I enable it.

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

## The cdp scripts

 There are two scripts for CDP neighbors.

- procurve-cdp-ne-report.py - This script creates a text file for the cdp neighbors
- procurve-cdp-ne-csv.py - This script creates a CSV file for the cdp neighbors

I wrote the script that creates the csv file so that you could use a spreadsheet or the Rainbow csv extension to sort the data.

Each of these scripts uses the same device-inventory file as the procurve-Config-pull.py script so there is no configuration needed. Just use:

- `python3 procurve-cdp-ne-report.py -s sitename`
- `python3 procurve-cdp-ne-csv.py -s sitename`

The reports are saved into the "Interface\neighbors" directory.

## The cdp neighbor text report

The first script creates a nicely formatted text file.

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

You can use it as is but since it's text so you can use grep to filter anything you want. For example, to filter on uplink ports on a Cisco switch:

`grep -Eir -b4 "GigabitEthernet1/1/" *cdp-report.txt`

Here is a snippet of the output:

```bash
Procurve-2920-48-cdp-report.txt-824-------------------------------
Procurve-2920-48-cdp-report.txt-855-destination_host: 64 00 f1 01 6f 80
Procurve-2920-48-cdp-report.txt-891-   management_ip: 192.168.1.1
Procurve-2920-48-cdp-report.txt-921-        platform: Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-...
Procurve-2920-48-cdp-report.txt:999:     remote_port: GigabitEthernet1/1/2
Procurve-2920-48-cdp-report.txt-1038-      local_port: 21
Procurve-2920-48-cdp-report.txt-1059-software_version: Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-...
Procurve-2920-48-cdp-report.txt-1137-
Procurve-2920-48-cdp-report.txt-1138-
Procurve-2920-48-cdp-report.txt-1139-------------------------------
Procurve-2920-48-cdp-report.txt-1170-destination_host: 3750x.pu.pri
Procurve-2920-48-cdp-report.txt-1201-   management_ip: 192.168.1.1
Procurve-2920-48-cdp-report.txt-1231-        platform: cisco WS-C3750X-48P
Procurve-2920-48-cdp-report.txt:1269:     remote_port: GigabitEthernet1/1/4
Procurve-2920-48-cdp-report.txt-1308-      local_port: 22
Procurve-2920-48-cdp-report.txt-1329-software_version: Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-...
```

Here is a screenshot of the csv report in Libre Office Calc:

<p align="left" width="100%">
<img width="60%" src="https://github.com/rikosintie/Discovery/blob/main/images/csv-snippet.png" alt="CSV format">
</p>

## cdp-ne.py

`procurve-cdp-ne-report.py` and `procurve-cdp-ne-csv.py` read a
device-inventory file and re-run their own commands per device. `cdp-ne.py`
instead reads the JSON `config-pull.py` already wrote to
`Interface/<host>-cdp.txt` (Cisco IOS and HP ProCurve both speak CDP; other
vendors don't) and prints a `port-map.py`-styled table:

```bash
python3 cdp-ne.py                        # every Interface/*-cdp.txt
python3 cdp-ne.py -f Interface/jc-mdf-1-cdp.txt
python3 cdp-ne.py -d 10.100.126.9        # PTR lookups via that server
python3 cdp-ne.py --no-dns               # skip PTR lookups
```

```text
Number of Entries: 5

Device Name: jc-mdf-1

Name               mgmt_address      Platform         R_Interface   L_Interface   Capabilities   DNS Name
─────────────────────────────────────────────────────────────────────────────────────────────────────────
SEP00085D65FF87    172.20.126.23     MINET_6940       Port 1        Gi1/0/13      Host Phone
─────────────────────────────────────────────────────────────────────────────────────────────────────────
JC-Core            10.100.126.253    WS-C4500X-16     Te1/1         Gi1/0/49      Ro Sw IGMP
```

R_Interface is the neighbor's port, L_Interface is the local one. Three
fields are tidied so the table fits a screen:

- **Platform** — the leading `cisco ` is stripped (`cisco WS-C4500X-16` ->
  `WS-C4500X-16`).
- **Capabilities** — `Router`/`Switch` are abbreviated (`Router Switch IGMP`
  -> `Ro Sw IGMP`); everything else is left readable.
- **Interfaces** — Cisco's long names are shortened
  (`GigabitEthernet1/0/13` -> `Gi1/0/13`, `TenGigabitEthernet1/1` -> `Te1/1`)
  to match what `show mac address-table` already prints.

Name is trimmed too: a bare FQDN drops its domain
(`JC-Core.tricommanagement.local` -> `JC-Core`), and a ProCurve neighbor that
sent no device id — just a chassis MAC — is reformatted as
`aa:bb:cc:dd:ee:ff` instead of `aa bb cc dd ee ff`.

The report is also written to `Interface/neighbors/<host>-cdp-ne.txt`.

> `procurve-cdp-ne-report.py` and `procurve-cdp-ne-csv.py` read field names
> (`neighbor_id`, `neighbor_address`, ...) that no longer match the current
> `-cdp.txt` captures — `cdp-ne.py` is the one to use going forward.
