# The Helper Scripts

----------------------------------------------------------------

![screenshot](img/Tux-Helper-scripts.resized.jpeg)

----------------------------------------------------------------

The helper scripts are a collection of python scripts that read data that the config-pull.py created and turn that raw data into useful reports.

## What files are created

After the `config-pull.py` script finishes, you can use the ***hostname-CR-data.txt*** files to get started planning. The script also creates JSON files for:

- Port Maps
- cdp neighbors
- lldp neighbors
- system data
- interface statistics
- interface mac addresses

In the data folder, below the port-maps folder, two text files are created:

- hostname-mac-address.txt - Output of show mac-address per port
- hostname-arp.txt - Output of show arp command

In the final folder

- hostname-ports.txt - The final output of two scripts for creating port maps

In the "Interface" folder

- hostname-cdp.txt - JSON format of the "show cdp ne det" command
- hostname-lldp.txt - JSON format of "show lldp info rem det" command
- hostname-system.txt - JSON format of "show system" command
- hostname-interface.txt - JSON format of "show interface"
- hostname-int-br.txt - JSON format of "show interface int br" command

This section will discuss the scripts that convert the JSON into reports.

In addition, there is a script to convert mac addresses between different formats

- `convert-mac.py`

----------------------------------------------------------------

## Warming the ARP cache with pinger.py

The port maps are only as complete as the ARP tables `config-pull.py`
collects, and a switch only has an ARP entry for a host that has sent
traffic recently. `pinger.py` reads a list of subnets and pings every host
in them so the gateways learn all the endpoints before the discovery run.

Put the subnets in a file (default `vlans.txt`), one per line. You can
paste straight from a switch —

```text
show run | i ^interface|^ ip address

interface Vlan10
 ip address 10.20.10.1 255.255.255.0
```

— or list them as `address mask` or CIDR:

```text
10.20.10.0 255.255.255.0
10.20.20.0/24
```

Blank lines, lines containing `interface`, and lines starting with `#` are
ignored, so `#` comments a subnet out. Subnets larger than `-m/--max-hosts`
addresses (default 2100, i.e. bigger than a `/21`) are skipped.

```bash
python3 pinger.py
python3 pinger.py -f user-subnets.txt
```

### All command-line options

```text
python3 pinger.py -h

usage: pinger.py [-h] [-f FILE] [-c COUNT] [-r RATE] [--in-order] [--tcp-ports TCP_PORTS] [--tcp-timeout TCP_TIMEOUT] [-m MAX_HOSTS]

Ping every host in the subnets listed in a file to warm the ARP cache.

options:
  -h, --help            show this help message and exit
  -f, --file FILE       subnet list file (default: vlans.txt)
  -c, --count COUNT     ICMP echo requests per host (default: 1, which is enough for ARP)
  -r, --rate RATE       max pings started per second, 0 = no limit (default: 20)
  --in-order            ping hosts low-to-high instead of in random order
  --tcp-ports TCP_PORTS
                        TCP ports to try on hosts that ignore ICMP, comma-separated (default: "9100"); pass "" to disable the TCP probe
  --tcp-timeout TCP_TIMEOUT
                        seconds to wait for each TCP connection (default: 1.0)
  -m, --max-hosts MAX_HOSTS
                        skip subnets with more addresses than this (default: 2100)
```

### Cross-platform examples

=== "Linux"

```text
python3 pinger.py
OS is Linux, sending 1 echo request per host
IP addresses have been randomized
Number of Subnets: 3
90 hosts to ping at 20/s (~4s of launches)

Pinging 30 hosts in 192.168.10.96/27
```

----------------------------------------------------------------

=== "macOS"

```text
python3 pinger.py

OS is Darwin, sending 1 echo request per host
IP addresses have been randomized
Number of Subnets: 3
90 hosts to ping at 20/s (~4s of launches)

Pinging 30 hosts in 192.168.10.96/27
```

----------------------------------------------------------------

=== "Windows"

```text
 python3 pinger.py -r 10

OS is Windows, sending 1 echo request per host
IP addresses have been randomized
Number of Subnets: 3
90 hosts to ping at 10/s (~9s of launches)

Pinging 30 hosts in 192.168.10.96/27
```

----------------------------------------------------------------

### Which subnets are worth pinging

Desktops, laptops, access points, IP phones, and surveillance cameras
send traffic all the time, so the switches already have a current ARP
entry for them. Pinging those subnets adds noise without adding much to
the port maps.

The devices that need warming up are the ones that sit quiet until
something talks to them:

- Door access controllers
- Building automation controllers (usually BACnet)
- Environmental monitoring systems (usually EMS)
- Any other IoT device that just waits for instructions

When these devices live on their own segmented VLANs, point `pinger.py` at
just those VLANs — there's no need to sweep the user subnets.

### Being gentle on EDR / NDR

Firing ICMP at every address in a subnet all at once looks exactly like a
horizontal scan and can get the machine running `pinger.py` alerted on or
quarantined at customers running CrowdStrike, SentinelOne, Darktrace, and
similar. Two arguments keep the sweep quiet:

- **`-r`, `--rate`** — the maximum number of pings started per second
  (default `20`). This is the setting that keeps the traffic looking like
  background noise instead of a scan. `--rate 0` removes the limit and
  starts every ping at once (the old, noisy behaviour).
- **`-c`, `--count`** — ICMP echo requests per host (default `1`). One
  request is enough to make the gateway learn the MAC; raise it only if
  you want more confidence that a host is really up.

Host order within each subnet is randomised by default (add `--in-order`
to disable). Before it starts, the script prints how many hosts it will
ping and roughly how long the launches will take at the chosen rate.

```bash
# One echo per host, 10 per second - light background traffic.
python3 pinger.py -r 10 -c 1
```

Even a paced sweep is quiet, not invisible — coordinate with the
customer's SOC first.

### Waking sleeping printers

Printers are the hardest devices to get an ARP entry for: their NICs drop
into a deep sleep and ignore ICMP echo, so even `-c 3` often comes back
empty. Almost every network printer, though, keeps TCP port 9100 (RAW /
JetDirect / AppSocket) open, and a bare TCP handshake to an open port
wakes the NIC where a ping will not.

After the ICMP pass, `pinger.py` opens one TCP connection to port 9100 on
every host that stayed silent and closes it immediately. Nothing is
written to the socket, so nothing prints. A host woken this way is
reported as `active (tcp/9100)`.

- **`--tcp-ports`** — comma-separated ports to try (default `9100`). Add
  `9101,9102` for multi-port external print servers. Pass `--tcp-ports ""`
  to switch the TCP probe off and go back to ICMP only.
- **`--tcp-timeout`** — seconds to wait for each connection (default
  `1.0`).

```bash
python3 pinger.py --tcp-ports 9100,9101,9102
```

A port-9100 sweep is lighter than a port scan but not invisible — some IDS
flag it as printer reconnaissance. Keep coordinating with the SOC.

**Waking one printer without a sweep.** If the customer would rather not
run `pinger.py` at all, a single printer can be woken with a one-line
Python call from the `Discovery` directory:

```bash
python3 -c "import pinger; print(pinger.tcp_probe('192.168.10.109', [9100], 1.0))"
```

Swap in the printer's address. It prints `9100` if the handshake
completed — the printer is now awake and its MAC is back on the switch —
or `None` if nothing answered on that port within a second. Nothing is
sent to the printer, so no page comes out.

**Or list every printer as a `/32`.** To wake a known set of printers on a
normal run without touching the rest of the subnet, put each one in
`vlans.txt` as a single-host entry:

```text
ip address 192.168.10.109/32
ip address 192.168.10.110/32
```

`pinger.py` expands a `/32` to just that one address, so the run hits
exactly the printers you listed.

----------------------------------------------------------------

## Creating Port maps

There are two scripts in the discovery folder:

- arp.py - converts the IP and Arp records into "key": "value" pairs

Here is an example:

```bash
{
    "04d590-0e77ab": "10.1.0.252",
    "883a30-76ce00": "10.154.1.3",
    "104f58-682100": "10.154.1.4",
    "b8d4e7-4c4900": "10.154.1.5",
}
```

The Mac Address is used for the key since MACs are unique, the IP Address is used for the value. It saves the data to hostname-Mac2IP.json in the data folder.

- port-map.py - Matches the Mac address in the hostname-Mac2IP.json file to the mac address in the hostname-mac-address.txt file.

The port maps return:

- Vlan ID
- IP Address
- MAC Address
- Interface
- Vendor ID

Here is an example of the port map:

```bash
Number of Entries: 83

Device Name: Test-Core
Vlan   IP Address       MAC Address       Interface   Vendor
--------------------------------------------------------------------------------
   1   10.154.66.1      7c0507-1f6ee4         C1      Pegatron
----------------------------------------------------------------------
   1   10.154.66.2      7c0507-1b45ea         C2      Pegatron
----------------------------------------------------------------------
   1   10.154.68.25     00c0b7-e4b43a         C4      American
----------------------------------------------------------------------
  75   10.154.23.241    000c29-e97dd1         C5      VMware
----------------------------------------------------------------------
```

Having this information makes identifying special devices such as HVAC controllers, Door access controllers, Cameras, etc. easier. It also allows you to verify that all devices are patched back into the correct port on the switch.

### Running the port map scripts

There are two general categories of switch deployments. The first is a distributed layer 3 deployment where every closet has a layer 3 router. In that case, the procurve-Config-pull has created an arp.txt file and mac-address.txt file for every switch and the script reads the same inventory file and matches the hostname-arp.txt file with the hostname-mac-address.txt file.

The second is a Core/IDF deployment where there is a layer 3 switch in an MDF and the closets are connected at layer 2. In this case, we have to use an argument in the port-map.py script to tell it which hostname-arp.txt file to use for each hostname-mac-address.txt file.

#### Running the arp.py script

One script handles the arp step for every supported vendor — it used to be split into procurve-arp.py, cisco-arp.py, and cx-arp.py. It finds the IP and MAC on each line by content rather than assuming a fixed column layout, so it doesn't matter whether the vendor prints Cisco-style `Internet <ip> <age> <mac> ARPA VlanN`, ProCurve-style `<ip> <mac> <type> <port>`, or Aruba CX-style `<ip> <mac> <vlan> <port> <state> <vrf>`.

Example of a distributed layer 3 deployment:

`python3 arp.py -s area1`

For a Core/IDF deployment, use `-c coreswitch`:

`python3 arp.py -s jc-edge -c JC-core`

The script will create the hostname-Mac2IP.json and will print some information to the screen. The first information is the file being processed and the number of IPs and the IPs sorted. Here is an example:

```bash
----------------------------------------------------------------------------------------
Reading devices from: /home/mhubbard/04_Tools/Discovery/port-maps/data/test-Core-arp.txt
----------------------------------------------------------------------------------------
Number of IP Addresses: 566
---------------------------
10.1.0.252
10.112.1.3
```

The next output is IP and MAC Addresses. Here is an example:

```bash
Number of IP and MAC Addresses: 566
-----------------------------------
10.1.0.252 04d590-0e77ab
10.112.1.3 883a30-76ce00
```

And finally, the IP, MAC and Manufacture. Here is an example:

```bash
Number of IP, MAC and Manufacture: 566
--------------------------------------
10.1.0.252 04d590-0e77ab Fortinet
10.112.1.3 883a30-76ce00 ArubaaHe
```

If you have a need for this information great, if not just ignore it.

#### Running the port-map.py script

One script handles the port-map step for every supported vendor — it used to be split into procurve-macaddr.py and cisco-macaddr.py (plus a third, cx-macaddr.py, for Aruba CX). It reads the hostname-Mac2IP.json and hostname-mac-address.txt files, detects each line's MAC format and column order rather than assuming a fixed layout, and creates the port maps — with a manufacturer lookup via the maintained `manuf2` package and, when a DNS server is available, a reverse-DNS name column.

`python3 port-map.py -s area1`

For a Core/IDF deployment, use `-c coreswitch`:

`python3 port-map.py -s jc-edge -c JC-core`

To resolve DNS names for the IP addresses in the port map, pass a DNS server with `-d`:

`python3 port-map.py -s jc-edge -c JC-core -d 192.168.10.222`

#### "UP with no learned MAC address" warning

A switch port can show `link_status: up` (and `protocol_status: up`) in
config-pull.py's `hostname-interface.json` capture while having no rows at
all in `hostname-mac-address.txt` — the port is physically connected, but
the device on it hasn't sent traffic recently enough to still be in the
switch's MAC address table. Without a flag for this, that host is just
silently missing from the port map.

port-map.py cross-references the two files for each device and, when it
finds any, prints a warning panel at the top of `hostname-ports.txt`,
right below the version banner:

```bash
╭───── ⚠ 5 interface(s) UP with no learned MAC address ─────╮
│ GigabitEthernet1/0/3                                       │
│ GigabitEthernet1/0/27                                      │
│ GigabitEthernet1/0/30                                      │
│ GigabitEthernet1/0/35                                      │
│ GigabitEthernet1/0/46                                      │
│                                                              │
│ Run pinger.py to refresh the mac address table              │
│ (uplinks/trunks may show up here too — eyeball those out)   │
╰──────────────────────────────────────────────────────────────╯
```

`pinger.py` is the recommended way to clear this — see [Warming the ARP
cache with pinger.py](#warming-the-arp-cache-with-pingerpy). Run it against
the site's subnets to generate traffic from those hosts, then re-run
config-pull.py and port-map.py to pick up the newly-learned MAC entries.

Uplink/trunk ports to other switches can legitimately show up in this list
too, since a per-interface MAC query on a trunk is often empty by design.
For now, eyeball those out; filtering them out automatically is a planned
refinement.

#### Updating the vendor (OUI) database

Both scripts above (arp.py, port-map.py) use the `manuf2` package to resolve a MAC address's manufacturer. The OUI database it ships with needs to be refreshed occasionally — newly-registered hardware won't have a vendor until it's in the database you have locally, and shows up as `None` instead. When that happens, run either:

```bash
python3 arp.py --update-manuf
python3 port-map.py --update-manuf
```

Any of these downloads the latest OUI and WFA (Wi-Fi Alliance) data and exits — none of them need `-s site`, and none touch any inventory files.

## Core/IDF deployment

In this case only the core switch has the arp records. The argument "-c coreswitch" is used to tell the switch to use the core-arp.txt file for all switches.

`python3 port-map.py -s area1 -c coreswitch`

----------------------------------------------------------------

## CDP Neighbor Reports

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

----------------------------------------------------------------

## LLDP neighbor Report

The Procurve switches support the Link Layer discovery protocol (lldp). LLDP is an open standard protocol so it will be found on most non-Cisco devices. If you are using Mac/Linux you can install the LLDP daemon and participate. I recommend doing that because it's very useful to be able to see what you are connected to. Also, if you run `show lldp` on a switch, you will see your device.

Here is my Ubuntu laptop as seen by the 2920:

```bash
  LocalPort | ChassisId          PortId             PortDescr SysName
  --------- + ------------------ ------------------ --------- ------------------
  24        | 54 bf 64 3b 9c 68  28 d0 ea 93 2a 42  wlp61s0   1S1K-G5-5587
```

Explanation of output:

- 24 - The port the lldp neighbor is connected to
- 54 bf 64 3b 9c 68 - The Chassis ID. In this case, it's the mac address of my laptop's ethernet interface
- 28 d0 ea 93 2a 42 - The port ID. This mac address of the wireless interface That is the interface that is connected to the network.
- wlp61s0 - The name of the wireless interface that is connected to the network.
- 1S1K-G5-5587 - The hostname of my laptop

### Installing LLDP on Ubuntu

This [blog](https://blog.marquis.co/posts/2015-09-07-installing-lldp-on-ubuntu/) is a good starting point for installing LLDP on Ubuntu. There are many public blogs on how to do it and a quick Google search or asking chatGPT will get you started.

### Installing LLDP on macOS

I use [homebrew](https://formulae.brew.sh/formula/lldpd) to install applications on the Mac and lldp is just `brew install lldp`.

### Enabling LLDP on the switch

By default lldp is  not running. If you want to use lldp you have to enable it using:

```bash
config t
lldp run
```

Then you can use the following command to see the lldp configuration:

```bash
show lldp config

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

You can customize LLDP using the following:

```bash
HP-2920-24G-PoEP(config)# lldp
 admin-status          Set the port operational mode.
 auto-provision        Configure radio port automatic provisioning.
 config                Set the TLV parameters to advertise on the specified ports.
 enable-notification   Enable notification on the specified ports.
 fast-start-count      Set the MED fast-start count in seconds.
 holdtime-multiplier   Set the holdtime multipler.
 refresh-interval      Set refresh interval/transmit interval in seconds.
 run                   Start LLDP on the device.
 top-change-notify     Enable LLDP MED topology change notification.
```

As you can see there are a lot of options available. Setting these options is beyond the scope of this article.

But it is interesting to note that you can change the basic Type, Length, Value (TLV) parameters that are advertised.

```bash
HP-2920-24G-PoEP(config)# lldp config
 [ethernet] PORT-LIST  Enter a port number, a list of ports or 'all' for all ports.
HP-2920-24G-PoEP(config)# lldp config 1
 basicTlvEnable        Specify the basic TLV List to advertise.
 dot1TlvEnable         Specify the 802.1 TLV list to advertise.
 dot3TlvEnable         Specify the 802.3 TLV list to advertise.
 ipAddrEnable          Specify the IP address to enable.
 medPortLocation       Configure the location ID information to advertise.
 medTlvEnable          Specify the MED TLV list to advertise.

HP-2920-24G-PoEP(config)# lldp config 1 basicTlvEnable
 port_descr            Port Description TLV
 system_name           System Name TLV
 system_descr          System Description TLV
 system_cap            System Capability TLV
 management_addr       Management Address TLV

```

### Running the script

The script uses the same device-inventory file as the procurve-Config-pull.py script so there is no configuration needed. Just use:

- `python3 procurve-lldp-ne-report.py -s sitename`

The report is saved into the "Interface\neighbors" directory.

Here is a snippet of the report:

```bash
           neighbor_sysname: 3750x.pu.pri
  remote_management_address: 10.254.34.17
      neighbor_chassis_type: mac-address
        neighbor_chassis_id: 64 00 f1 01 6f 80
               system_descr: Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-M...
            neighbor_portid: Gi1/0/1
                 local_port: 1
               system_descr: Cisco IOS Software, C3750E Software (C3750E-UNIVERSALK9-M...
                       PVID: 850
                 port_descr: GigabitEthernet1/0/1
system_capabilities_enabled: bridge, router
```

I left the labels just as they are in the `show command`. If you want to change them it's fairly obvious in the script. For example, to change "remote_management_address" to "remote IP address" look for this line:

`remote_management_address = f'{"remote_management_address: " :>29}{data[counter]["remote_management_address"]}'`

and change "remote_management_address: " to "remote IP address: "

----------------------------------------------------------------

## The System Report

The system report will be useful for filling out the Change request form or a transmittal. Again, being a plain text file you will be able to use grep to filter. For example:

`grep -Eir -b4 "serial number" *system-report.txt`

To pull a list of serial numbers from the system reports.

Here is a snippet of the system report:

```bash
        Hostname: HP-2920-24G-PoEP
   snmp location: Home Lab
    snmp contact: Michael Hubbard
 MAC address age: 300
        timezone: -480
   daylight_rule: Continental-US-and-Canada
software_version: WB.16.10.0023
     rom_version: WB.16.03
     mac address: 98f2b3-fe8880
   serial number: SG78FLXH0B
   system_uptime: 3 hours
 cpu_utilization: 47
        mem_free: 40,344,656
```

----------------------------------------------------------------

## The Interface scripts

There are two scripts for interfaces:

- procurve-10Mb.py - Creates a list of interfaces that are running at 10Mbps full or half duplex.
- procurve-interface-in-use.py - Creates a list of interfaces that have a "total_byte" count not equal to 0.

I wrote the script that creates the 10Mbps list because smartrate and mGig ports don't support 10Mbps rates. From personal experience I can tell you that it's better to find out in the discovery phase than the deployment phase.

Devices running at 10Mbps full or half are usually door access controllers or Building Automation controllers. You will not have any success getting them replaced before the deployment phase begins. To verify you can use the port maps and look up the manufacturer.

The interface report for "in use" was requested so that decisions about consolidating interfaces could be made. It has the "uptime" of the switch as the first line in the file so that there is some context about the zero bytes. For example, if the switch has an uptime of a few days then the ports not in use could be employees on vacation for devices that are used infrequently.

Each of these scripts uses the same device-inventory file as the procurve-Config-pull.py script so there is no configuration needed. Just use:

- `python3 procurve-10Mb.py -s sitename`
- `python3 procurve-interface-in-use.py -s sitename`

The reports are saved into the "CR-data" directory.

### The 10Mbps interfaces report

This script creates a simple text file with the filename format of "hostname-10Mb-Ports.txt". For example:

`Procurve-2930-48-10Mb-Ports.txt`

Here is a snippet of the cdp neighbor text report:

```bash
Interface 2 - 10FDx
Interface 3 - 10HDx
```

### The ports in use report

This script creates a simple text file with the filename format of hostname-Port-data.txt. For example:

`Procurve-2920-48-Port-data.txt`

Here is a snippet of the cdp neighbor text report:

```bash

System Uptime: 3 hours

Number of Interfaces with traffic: 5
Interface 1 - total_bytes 1,510,198
Interface 2 - total_bytes 0
Interface 3 - total_bytes 0
Interface 4 - total_bytes 0
Interface 5 - total_bytes 0
Interface 6 - total_bytes 0
Interface 7 - total_bytes 1,054,112
```

### The port migration report

migrate-ports.py builds a config snippet to help migrate a switch from Cisco IOS to Aruba CX. It's Cisco IOS only right now (checks the vendor column in the device-inventory file) — the source side of the migration. If no `cisco_ios` device is found in the device-inventory file, it prints a message saying so instead of silently producing no output.

It looks at every interface in `Interface/<hostname>-interface.json` and, for ones that are up, includes two kinds:

- **Uplinks on module 1** — matched by a `[0-8]/1/[0-9]{1,2}` pattern, e.g. `Gi1/1/3`. This is meant to catch trunk/uplink ports specifically, not every access port.
- **SVIs** — any `VlanN` interface.

For each match it writes an `interface` / `description` / `ip address` / `exit` block. The description line is always written, even if blank on the switch — there's no check for whether one is actually set. The IP address line is only included if the interface has one (VLANs typically do, physical uplinks typically don't).

Uplink interface names get shortened to just the last 5 characters (`Gi1/1/3` becomes `1/1/3`, dropping the interface type) — this is deliberate, not a quirk to work around: Aruba CX doesn't use a "Gi"-style type prefix on interface names at all, so the shortened form is already the correct CX syntax to paste in as-is. SVI names are converted from Cisco's `VlanN` to Aruba CX's `vlan N` — lowercase, with a space before the number — since that's the syntax CX actually expects for both the `vlan` block and the `interface vlan` reference.

`python3 migrate-ports.py -s sitename`

The output is saved as `Interface/<hostname>-interface-migrate.txt`. Here is an example:

```bash
interface 1/1/4
description < Fiber Link to Z420 >

 exit
interface vlan 10
description < Management >
ip address 192.168.10.253
 exit
```

----------------------------------------------------------------

## Parsing Aruba CX logs

`CX-Log-Parse.py` takes a syslog export already saved to disk and turns it into a CSV. `CX-Log-Parse-API.py` does the same thing, but can also pull the log directly from a switch over the REST API instead of starting from a file. Both use the same regex to split each log line into: date, time, timezone, hostname, process, PID, event type, event ID, log level, module, interface, and message.

`python3 CX-Log-Parse.py -f logfile.txt`

Raw CX syslog lines pack the date, time, fractional seconds, and UTC offset into one unbroken token, e.g. `2024-05-15T21:46:01.398675-07:00`. There's no delimiter between the seconds and the timezone, so searching or sorting by date or time alone in a text editor means eyeballing a wall of similar-looking timestamps — you can't easily filter "just today" or "just this hour" without regex. Splitting Date, Time, and Timezone into their own CSV columns means a spreadsheet program (or a CSV tool like `csvlens`) can sort, filter, and search each of those fields independently, the same way it can for hostname, interface, or log level.

### Pulling logs directly from a switch

`CX-Log-Parse-API.py -i <ip>` logs into the switch's REST API to pull logs instead of reading a local file, which means it needs a password. The password is never accepted as a plaintext command-line argument — that would leave it sitting in plain view in shell history and process listings. Instead, use one of:

- `-p 1` — prompts for the password interactively (it isn't echoed to the terminal).
- The `cyberARK` environment variable — set it once per shell session with `export cyberARK=your_password`, and every run in that session picks it up automatically with no prompt.

If neither is set, the script prints a reminder of both options and exits instead of falling back to a default password.

----------------------------------------------------------------

## Daily discovery status snapshot

On a long discovery — multiple sites, or multiple wiring closets — the customer will want a daily update on how many devices have been discovered and had data pulled so far. `filenames.py` lists the files present in each of the output directories (`CR-data`, `Interface`, `port-maps/Final`, `Running`) and saves each directory's filename list to its own CSV and Excel file, so a status snapshot can be shared without opening every folder by hand.

`python3 filenames.py`

The output files are named after the directory they came from (e.g. `Running/Running.csv`, `Running/Running.xlsx`), except for `port-maps/Final`, which is saved as `port-maps.csv`/`port-maps.xlsx`.

----------------------------------------------------------------

## Convert MAC addresses

This simple script takes 1 argument, a MAC address in any of the following formats and returns it in all of the formats.

- 64:e8:81:43:cc:4e
- 64e881-43cc4e
- 64e8.8143.cc4e
- 64-e8-81-43-cc-4e
- 64e88143cc4e

```bash
python3 convert-mac.py --mac 64:e8:81:43:cc:4e
64:e8:81:43:cc:4e
64e881-43cc4e
64e8.8143.cc4e
64-e8-81-43-cc-4e
64e88143cc4e
```

----------------------------------------------------------------
