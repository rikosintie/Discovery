# The Helper Scripts

----------------------------------------------------------------

![screenshot](img/Tux-Helper-scripts.resized.jpeg)

----------------------------------------------------------------

The helper scripts are a collection of python scripts that read data that the config-pull.py created and turn that raw data into useful reports.

Every report here is plain text, so the `grep` examples throughout this
page work unchanged on Windows too, once you've
[installed Coreutils for Windows](../Getting_Started.md#install-coreutils-for-windows) —
see that section for the one common gotcha (`sort` needs a `.exe` suffix).

## What files are created

Every folder mentioned below is created automatically the first time a
script writes to it — most of them are gitignored, so a fresh clone won't
have them yet, and that's expected. There's nothing to create by hand.

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

In the "pinginfo" folder, below the port-maps folder

- hostname-pinginfo.txt - A [PingInfoView](https://www.nirsoft.net/utils/multiple_ping_tool.html) import file pairing each reachable IP with its DNS name (or MAC address, if no DNS name resolves) — for verifying hosts pre/post cutover

In the "Interface" folder

- hostname-cdp.txt - JSON format of the "show cdp ne det" command
- hostname-lldp.txt - JSON format of "show lldp info rem det" command
- hostname-system.txt - JSON format of "show system" command
- hostname-interface.txt - JSON format of "show interface"
- hostname-int-br.txt - JSON format of "show interface int br" command

In addition, there is a script to convert mac addresses between different formats

- `convert-mac.py`

----------------------------------------------------------------

## What's covered where

The rest of the helper scripts are broken out into their own pages:

- [Warming the ARP Cache with pinger.py](pinger.md) — pre-warming ARP tables before a discovery run
- [Creating Port Maps](port-maps.md) — arp.py, port-map.py, merging external ARP data, PingInfoView/gping/fping
- [CDP Neighbor Reports](cdp-reports.md)
- [LLDP Neighbor Report](lldp-reports.md)
- [Topology Diagrams with topo-map.py](topology-maps.md)
- [The System Report](system-report.md)
- [The Interface Scripts](interface-reports.md) — 10Mbps interfaces, ports in use, port migration
- [Parsing Aruba CX Logs](aruba-cx-logs.md)
- [Daily Discovery Status Snapshot](daily-status.md)
- [Convert MAC Addresses](convert-mac.md)
