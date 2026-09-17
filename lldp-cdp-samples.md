# CDP / LLDP Sample Outputs — Aruba CX, Nexus, Cisco SG, Junos, Ruckus FastIron

Composited from Aruba/Cisco/Juniper/Ruckus documentation, ntc-templates test
fixtures, and community threads — not a single live pull. Each block is
shaped to be realistic and internally consistent, and mixes a switch,
an AP, and a phone neighbor per platform where that platform supports it.
Use these to shape/validate TextFSM templates before you get real captures
from site.

---

## Aruba CX (AOS-CX)

### `show lldp neighbor-info` (summary)

```
switch# show lldp neighbor-info
LLDP Neighbor Information
=========================
Total Neighbor Entries       : 3
Total Neighbor Entries Deleted : 0
Total Neighbor Entries Dropped : 0
Total Neighbor Entries Aged-Out : 0

LOCAL-PORT  CHASSIS-ID          PORT-ID             PORT-DESC           TTL  SYS-NAME
--------------------------------------------------------------------------------------
1/1/1       70:72:cf:a4:7d:50   1/1/1               1/1/1               120  CORE-SW01
1/1/10      38:ca:84:56:4e:47   3601                                    120  AP-Lobby-325
1/1/15      6c:0b:5e:5b:e1:69   Port 1                                  120  SEP001A2B3C4D5E
```

### `show lldp neighbor-info <port>` (detail, one at a time — AP example)

```
switch# show lldp neighbor-info 1/1/10
Port                              : 1/1/10
Neighbor Entries                  : 1
Neighbor Entries Deleted          : 0
Neighbor Entries Dropped          : 0
Neighbor Entries Aged-Out         : 0
Neighbor Chassis-Name             : 38:ca:84:56:4e:47
Neighbor Chassis-Description      : ArubaOS (MODEL: 325), Version 8.11
Neighbor Chassis-ID               : 38:ca:84:56:4e:47
Neighbor Management-Address       : 10.10.20.44
Chassis Capabilities Available    : Bridge, WLAN
Chassis Capabilities Enabled      : WLAN
Neighbor Port-ID                  : 38:ca:84:56:4e:47
Neighbor Port-Desc                : eth0
TTL                                : 120
Neighbor Port VLAN ID              : 20
Neighbor PoE information          : DOT3
Neighbor Power Type                : TYPE2 PD
Neighbor Power Priority            : Unknown
Neighbor Power Source              : Primary
PD Requested Power Value           : 25.0 W
PSE Allocated Power Value          : 25.0 W
Neighbor Power Supported           : Yes
Neighbor Power Enabled             : Yes
Neighbor Power Class               : 5
```

### `show lldp neighbor-info detail` (all ports, switch neighbor)

```
switch# show lldp neighbor-info detail
LLDP Neighbor Information
=========================
Total Neighbor Entries        : 6
Total Neighbor Entries Deleted : 2
Total Neighbor Entries Dropped : 0
Total Neighbor Entries Aged-Out : 2
--------------------------------------------------------------------------------
Port                              : 1/1/1
Neighbor Entries                  : 1
Neighbor Chassis-Name             : CORE-SW01
Neighbor Chassis-Description      : Aruba CX 6300M, Version FL.10.13.1010
Neighbor Chassis-ID               : 38:11:17:1a:d5:00
Neighbor Management-Address       : 38:11:17:1a:d5:00
Chassis Capabilities Available    : Bridge, Router
Chassis Capabilities Enabled      : Bridge, Router
Neighbor Port-ID                  : 1/1/4
Neighbor Port-Desc                : 1/1/4
Neighbor Port VLAN ID              : 1
Neighbor Port VLAN Name            : DEFAULT_VLAN_1
Neighbor Port MFS                  : 1500
TTL                                 : 120
Neighbor Mac-Phy details
  Neighbor Auto-neg Supported      : true
  Neighbor Auto-Neg Enabled        : true
  Neighbor Auto-Neg Advertised     : 1000 BASE_TFD, 100 BASE_T4, 10 BASET_FD
  Neighbor MAU type                : 1000 BASETFD
--------------------------------------------------------------------------------
Port                              : 1/1/15
Neighbor Entries                  : 1
Neighbor Chassis-Name             : SEP001A2B3C4D5E
Neighbor Chassis-Description      : Cisco IP Phone 8865, V1, SIP 14.2
Neighbor Chassis-ID               : 6c:0b:5e:5b:e1:69
Neighbor Management-Address       :
Chassis Capabilities Available    : Telephone, Bridge
Chassis Capabilities Enabled      : Telephone, Bridge
Neighbor Port-ID                  : Port 1
Neighbor Port-Desc                : Port 1 (LAN)
TTL                                 : 120
Neighbor Port VLAN ID              : 20
Neighbor PoE information          : DOT3
Neighbor Power Type                : TYPE2 PD
PD Requested Power Value           : 15.4 W
PSE Allocated Power Value          : 15.4 W
```

> ArubaOS-CX has no `show cdp ...` — CDP is not implemented; AOS-CX only speaks LLDP (and reads incoming CDP from Cisco phones/APs into the LLDP neighbor table if `lldp` compatibility is on, but it never emits `show cdp` itself). Don't build a `cisco_cdp`-style command for CX in the platform matrix.

---

## Cisco Nexus (NX-OS)

### `show cdp neighbors` (summary)

```
switch# show cdp neighbors
Capability Codes: R - Router, T - Trans-Bridge, B - Source-Route-Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater,
                  V - VoIP-Phone, D - Remotely-Managed-Device,
                  s - Supports-STP-Dispute

Device-ID           Local Intrfce  Hldtme Capability  Platform      Port ID
N9K-SPINE1           mgmt0         168    R S I s     N9K-C93180YC-FX Eth1/1
AP-Lobby-325.local    Eth1/10       120    B           AIR-AP325      Gig0
SEP001A2B3C4D5E       Eth1/15       120    T           Cisco IP Phone 8865 Port 1
```

### `show cdp neighbors detail` (one entry — switch)

```
switch# show cdp neighbors detail
-------------------------
Device ID:N9K-SPINE1(FDO12345678)
Sysname : N9K-SPINE1
Interface address(es):
    IPv4 Address: 10.0.0.1
Platform: N9K-C93180YC-FX, Capabilities: Router Switch IGMP Supports-STP-Dispute
Interface: mgmt0, Port ID (outgoing port): Ethernet1/1
Holdtime: 168 sec

Version:
Cisco Nexus Operating System (NX-OS) Software, Version 10.3(2)

Advertisement Version: 2
VTP Management Domain: ''
Duplex: full
```

### `show cdp neighbors detail` (phone entry)

```
-------------------------
Device ID:SEP001A2B3C4D5E
Sysname :
Interface address(es):
    IPv4 Address: 10.10.20.101
Platform: Cisco IP Phone 8865, Capabilities: Host Phone
Interface: Ethernet1/15, Port ID (outgoing port): Port 1
Holdtime: 120 sec

Version:
sip88xx.14-2-1

Advertisement Version: 2
Duplex: full
Power drawn: 15.400 Watts
```

### `show lldp neighbors` (summary) — Nexus also runs standards-based LLDP

```
switch# show lldp neighbors
Capability codes:
    (R) Router, (B) Bridge, (T) Telephone, (C) DOCSIS Cable Device
    (W) WLAN Access Point, (P) Repeater, (S) Station, (O) Other

Device ID            Local Intf      Hold-time  Capability   Port ID
N9K-SPINE1            mgmt0           120        BR           Ethernet1/1
AP-Lobby-325          Eth1/10         120        WB           38:ca:84:56:4e:47
SEP001A2B3C4D5E       Eth1/15         120        T            Port 1
Total entries displayed: 3
```

### `show lldp neighbors interface ethernet 1/10 detail` (AP)

```
switch# show lldp neighbors interface ethernet 1/10 detail
Chassis id: 38:ca:84:56:4e:47
Port id: 38:ca:84:56:4e:47
Local Port id: Eth1/10
Port Description:  eth0
System Name: AP-Lobby-325
System Description: ArubaOS (MODEL: 325), Version 8.11.2.1
Time remaining: 111 seconds
System Capabilities: B, W
Enabled Capabilities: W
Management Address: 10.10.20.44
Vlan ID: 20
```

---

## Cisco SG (Small Business 300/350 series, "Sx300" CLI)

Cisco SG/SF Small Business switches run a stripped-down CLI (ntc-templates
calls this platform `cisco_s300`) — no `show cdp neighbors` support at all
(no CDP stack), and `show lldp neighbors` output is table-only; there is no
IOS-style `detail` keyword. Plan your TextFSM/netmiko `platform` field for
this device separately from `cisco_ios`.

### `show lldp neighbors`

```
switch#show lldp neighbors
Port         Device ID              Port ID          System Name           Capabilities   TTL
------       ---------------------  ---------------  --------------------  -------------  ---
gi1          00:1a:1e:12:34:56      GigabitEthernet1  CORE-SW01             B,R            120
gi10         6c:0b:5e:5b:e1:69      Port 1            SEP001A2B3C4D5E       T              120
gi24         38:ca:84:56:4e:47      3601              AP-Breakroom-325      B,W            120
```

### `show lldp neighbors gi10` (single-port form; still table, no free-form detail)

```
switch#show lldp neighbors gi10
Port         Device ID              Port ID          System Name           Capabilities   TTL
------       ---------------------  ---------------  --------------------  -------------  ---
gi10         6c:0b:5e:5b:e1:69      Port 1            SEP001A2B3C4D5E       T              120
```

There's also `show lldp neighbors ethernet gi10` and `show lldp interface`
(operational status only, no remote-device data) on this platform — but no
`remote-device` or `detail` keyword like the enterprise IOS/IOS-XE CLI. If
your topo-map.py currently assumes IOS's multi-line detail block for every
Cisco device, the SG boxes will need their own TextFSM template (this is
exactly the `cisco_s300_show_lldp_neighbors.textfsm` template in
ntc-templates — worth pulling that one in directly rather than hand-rolling).

---

## Juniper Junos (EX / SRX / MX)

### `show lldp neighbors` (summary)

```
user@switch> show lldp neighbors
Local Interface    Parent Interface    Chassis Id          Port info    System Name
ge-0/0/0.0         -                   00:1a:1e:12:34:56   ge-0/0/1     CORE-SW01
ge-0/0/10.0        -                   38:ca:84:56:4e:47   3601         AP-Conf-Rm-325
ge-0/0/22.0        -                   6c:0b:5e:5b:e1:69   Port 1       SEP001A2B3C4D5E
```

### `show lldp neighbors interface ge-0/0/22.0 detail` (phone)

```
user@switch> show lldp neighbors interface ge-0/0/22.0 detail
LLDP Neighbor Information:
Local Information:
Index: 23 Time to live: 120 Time mark: Thu Sep 10 09:14:02 2026 Age: 4 secs
Local Interface    : ge-0/0/22.0
Parent Interface   : -
Local Port ID      : 601
Ageout Count       : 0

Neighbour Information:
Chassis type       : Mac address
Chassis ID         : 6c:0b:5e:5b:e1:69
Port type          : Locally assigned
Port ID            : Port 1
Port description   : Port 1 (LAN)
System name        : SEP001A2B3C4D5E
System Description : Cisco IP Phone 8865, V1, SIP 14.2
System capabilities Supported: Bridge, Telephone
                    Enabled  : Bridge, Telephone
Management address :
  Address type       : IPv4
  Address            : 10.10.20.101
  Interface number   : 601
  Interface Subtype  : Locally assigned
  OID                : 1.3.6.1.2.1.4.20.1.1
Media Endpoint Discovery Information:
  Device type        : Class III
  Power type          : PD Device
  Power source        : Primary Power Source
  Power priority      : High
  Power value         : 15400 (mWatts)
```

### `show lldp neighbors interface ge-0/0/10.0 detail` (AP)

```
user@switch> show lldp neighbors interface ge-0/0/10.0 detail
LLDP Neighbor Information:
Local Information:
Index: 11 Time to live: 120 Time mark: Thu Sep 10 09:12:41 2026 Age: 9 secs
Local Interface    : ge-0/0/10.0
Parent Interface   : -
Local Port ID      : 589
Ageout Count       : 0

Neighbour Information:
Chassis type       : Mac address
Chassis ID         : 38:ca:84:56:4e:47
Port type          : Interface alias
Port ID            : 3601
Port description   : eth0
System name        : AP-Conf-Rm-325
System Description : ArubaOS (MODEL: 325), Version 8.11.2.1
System capabilities Supported: Bridge, WLAN Access Point
                    Enabled  : WLAN Access Point
Management address :
  Address type       : IPv4
  Address            : 10.10.20.55
```

> Junos also supports `show cdp neighbors` / `show cdp neighbors detail` on
> some EX/SRX platforms (Junos speaks a CDP-compatible mode primarily to
> interoperate with Cisco phones/APs), but it's off by default and much less
> commonly enabled than LLDP in Junos shops — confirm with `show cdp` first;
> if it returns "CDP is not enabled" don't bother scraping it.

---

## Ruckus / CommScope FastIron (ICX)

FastIron speaks both CDP and LLDP, and the CLI is IOS-adjacent but not
identical (e.g. `show lldp neighbors detail ports ethernet 1/1/9` scoping,
and the `Lcl Port` header instead of `Local Interface`).

### `show lldp neighbors` (summary)

```
device#show lldp neighbors
Lcl Port  Chassis ID          Port ID              Port Description          System Name
1/1/1     0000.0126.2057      1/1/2                10GigabitEthernet1/1/2    ICX-CORE-02
1/1/9:1   38ca.8456.4e47      3601                                           AP-Warehouse-325
1/1/12    6c0b.5e5b.e169      Port 1                                          SEP001A2B3C4D5E
```

### `show lldp neighbors detail ports ethernet 1/1/12` (phone)

```
device#show lldp neighbors detail ports ethernet 1/1/12
Local port: 1/1/12
 Neighbor : 6c0b.5e5b.e169, TTL 118 seconds
  + Chassis ID (MAC address)      : 6c0b.5e5b.e169
  + Port ID (Locally assigned)    : Port 1
  + Time to live                  : 120 seconds
  + System name                   : "SEP001A2B3C4D5E"
  + System description            : "Cisco IP Phone 8865, V1, SIP 14.2"
  + Port description              : "Port 1 (LAN)"
  + System capabilities           : bridge, telephone
    Enabled capabilities          : bridge, telephone
  + Management address (IPv4)     : 10.10.20.101
  + MED device type               : Endpoint Class III
  + MED Power                     : PD device, priority high, source primary, value 15.4 W
```

### `show lldp neighbors detail ports ethernet 1/1/9:1` (AP)

```
device#show lldp neighbors detail ports ethernet 1/1/9:1
Local port: 1/1/9:1
 Neighbor : 38ca.8456.4e47, TTL 92 seconds
  + Chassis ID (MAC address)      : 38ca.8456.4e47
  + Port ID (MAC address)         : 38ca.8456.4e47
  + Time to live                  : 120 seconds
  + System name                   : "AP-Warehouse-325"
  + Port description              : "eth0"
  + System capabilities           : bridge, wlan access point
    Enabled capabilities          : wlan access point
  + 802.3 MAC/PHY                 : auto-negotiation supported, but disabled
    Operational MAU type          : Other
  + Management address (IPv4)     : 10.10.20.60
```

### `show cdp neighbors` (summary — FastIron's CDP is IOS-flavored)

```
device#show cdp neighbors
Capability Codes: R - Router, T - Trans Bridge, B - Source Route Bridge
                  S - Switch, H - Host, I - IGMP, r - Repeater, P - Phone

Device ID        Local Intrfce   Holdtme  Capability  Platform         Port ID
ICX-CORE-02       1/1/1           157      R S         ICX7650-48ZP     1/1/2
SEP001A2B3C4D5E   1/1/12          142      H P         Cisco IP Phone 8865  Port 1
```

### `show cdp neighbors detail` (phone entry)

```
device#show cdp neighbors detail
-------------------------
Device ID: SEP001A2B3C4D5E
Entry address(es):
  IP address: 10.10.20.101
Platform: Cisco IP Phone 8865,  Capabilities: Host Phone
Interface: 1/1/12,  Port ID (outgoing port): Port 1
Holdtime: 142 sec

Version:
sip88xx.14-2-1

advertisement version: 2
Duplex: full
Power drawn: 15.400 Watts
```

---

## Quick platform-support matrix

| Platform     | CDP?                       | LLDP?                          | Detail granularity |
|--------------|-----------------------------|---------------------------------|---------------------|
| Aruba CX     | No (receive-only, no `show cdp`) | Yes — `neighbor-info [port] [detail]` | Per-port or full detail dump |
| Cisco Nexus  | Yes — full IOS-style        | Yes — full IOS-style            | Per-interface `detail` |
| Cisco SG     | No                           | Yes — table only, no `detail`   | None — flat table only |
| Juniper Junos| Sometimes (off by default)  | Yes — `detail` since 19.1R2     | Per-interface `detail`, richest MED data |
| Ruckus FastIron | Yes — IOS-flavored       | Yes — `detail ports ethernet x/x/x` scoping required for detail | Per-port only, no "detail" for all ports at once on older code |

A few gotchas worth building into topo-map.py's parser selection logic:

- **Aruba CX has no CDP at all** — don't even attempt `show cdp` against it; it'll just error.
- **Cisco SG has no LLDP/CDP detail mode** — you're stuck with the flat table, so management IP/PoE/capability strings you get from Nexus or Junos won't exist here. If topo-map.py assumes every Cisco device gives you a detail block, the SG units will silently short you on fields.
- **Ruckus FastIron's LLDP `detail` needs a port scope** on some code trains (`ports ethernet x/x/x`) rather than dumping details for all neighbors in one shot — check your specific FastIron version before assuming `show lldp neighbors detail` alone gives you everything.
- **Phone entries are the most schema-fragile** across all five: system-name format (`SEPxxxxxxxxxxxx` vs blank), PoE wattage fields, and whether MED capability data appears at all vary a lot phone-to-phone even on the same switch platform.
