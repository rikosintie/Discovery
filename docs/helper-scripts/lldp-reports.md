# LLDP neighbor Report

----------------------------------------------------------------

![tux-lldp](img/tux-lldp.jpeg)

----------------------------------------------------------------

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

## Installing LLDP on Ubuntu

This [blog](https://blog.marquis.co/posts/2015-09-07-installing-lldp-on-ubuntu/) is a good starting point for installing LLDP on Ubuntu. There are many public blogs on how to do it and a quick Google search or asking chatGPT will get you started.

## Installing LLDP on macOS

I use [homebrew](https://formulae.brew.sh/formula/lldpd) to install applications on the Mac and lldp is just `brew install lldp`.

## Enabling LLDP on the switch

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

## Running the script

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

## lldp-ne.py

Same idea as `cdp-ne.py`, reading the JSON `config-pull.py` wrote to
`Interface/<host>-lldp.txt` instead of re-querying each device:

```bash
python3 lldp-ne.py                        # every Interface/*-lldp.txt
python3 lldp-ne.py -f Interface/jc-mdf-1-lldp.txt
python3 lldp-ne.py -d 10.100.126.9        # PTR lookups via that server
python3 lldp-ne.py --no-dns               # skip PTR lookups
```

```text
Number of Entries: 10

Device Name: jc-idf-2

Name                       mgmt_address      Platform         R_Interface      L_Interface   Capabilities   DNS Name
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
regDN 2148,MINET_6940      172.20.126.29     MINET_6940       0008.5d65.f3e9   Gi1/0/8       B,T
JC-IDF-1                   10.100.126.236                     Te1/1            Gi1/0/49      B,R
```

Same columns as `cdp-ne.py`. R_Interface comes from `neighbor_port_id` on
Cisco (already short, or a MAC for a device like a phone that reports one
instead of a port name) and from `neighbor_interface` on ProCurve, which has
no `neighbor_port_id` field. Capabilities are LLDP's own letter flags (`B,T`
= bridge, telephone) or short words — already compact, so only
`bridge, router` gets collapsed to `bridge,router`. Platform and interface
names are tidied the same way as `cdp-ne.py`.

A device with LLDP turned off (`% LLDP is not enabled`) is skipped with a
message instead of erroring.

The report is also written to `Interface/neighbors/<host>-lldp-ne.txt`.

> `procurve-lldp-ne-report.py` reads field names (`neighbor_sysname`,
> `remote_management_address`, ...) that no longer match the current
> `-lldp.txt` captures — `lldp-ne.py` is the one to use going forward.
