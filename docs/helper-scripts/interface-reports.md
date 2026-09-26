# The Interface scripts

There are two scripts for interfaces:

- 10Mb-ports.py - Creates a list of interfaces that are running at 10Mbps full or half duplex.
- interfaces-in-use.py - Creates a list of interfaces that have ever passed traffic.

I wrote the script that creates the 10Mbps list because smartrate and mGig ports don't support 10Mbps rates. From personal experience I can tell you that it's better to find out in the discovery phase than the deployment phase.

Devices running at 10Mbps full or half are usually door access controllers or Building Automation controllers. You will not have any success getting them replaced before the deployment phase begins. To verify you can use the port maps and look up the manufacturer.

The interface report for "in use" was requested so that decisions about consolidating interfaces could be made. It has the switch's "uptime" as the first line in the file so that there is some context about the zero-traffic ports. For example, if the switch has an uptime of a few days then the ports not in use could be employees on vacation for devices that are used infrequently.

Both scripts were rewritten to match the standalone style of `cdp-ne.py`/`lldp-ne.py`/`topo-map.py`: no device-inventory file, no site name — each reads every matching `Interface/*.json`/`*.txt` capture directly. `interfaces-in-use.py` replaces `procurve-interface-in-use.py`, which pointed at `Interface/<host>-interface.txt` — a filename `config-pull.py` stopped writing once this capture moved to JSON, so that script could never have found a file to read, on any vendor.

```bash
python3 10Mb-ports.py                        # every Interface/*-int_br.txt
python3 10Mb-ports.py -f Interface/2920-int_br.txt
python3 interfaces-in-use.py                 # every Interface/*-interface.json
python3 interfaces-in-use.py -f Interface/2920-interface.json
```

Both scripts save their reports into the "CR-data" directory.

## The 10Mbps interfaces report

Reads ProCurve, Cisco IOS/XE, and Cisco Small Business/S300 captures.
`int_br.txt` carries no vendor field, so the script detects which of the
three shapes it's looking at from the keys already in the JSON:

- **ProCurve** folds speed and duplex into one field: `"mode": "10FDx"`.
- **Cisco IOS/XE** keeps them separate: `"speed": "10"` or `"a-10"`
  (auto-negotiated), `"duplex": "full"`/`"a-full"` etc. — `"auto"`/`"auto"`
  means the port never resolved a speed (nothing plugged in), not a 10Mb
  link.
- **Cisco S300** also keeps them separate, but with its own capitalization
  and a `linkstate` field instead of `status`.

`config-pull.py` collects this same file for `cisco_nxos`, `aruba_aoscx`,
and `aruba_osswitch` too, but none of those three vendors have a `show
interfaces status` textfsm template anywhere in this project as of this
writing, so their captures come back as unparsed raw text rather than
structured JSON. `10Mb-ports.py` detects that case and says so —
"not structured data (no textfsm parser for this platform's...)" — instead
of silently skipping the host or guessing at a format nobody has captured.

The output format is unchanged: a simple text file named
"hostname-10Mb-Ports.txt". For example:

`Procurve-2930-48-10Mb-Ports.txt`

Here's a snippet:

```bash
Interface 2 - 10FDx
Interface 3 - 10HDx
```

Running it with no arguments sweeps every capture in `Interface/` in one
pass — ProCurve and Cisco side by side, real output from a mixed-vendor site:

```bash
python3 10Mb-ports.py
No 10Mbps interfaces found for 2920
No 10Mbps interfaces found for jc-core
No 10Mbps interfaces found for jc-idf-1
No 10Mbps interfaces found for jc-idf-2
No 10Mbps interfaces found for jc-idf-cam-1
Writing CR data to CR-data/jc-mdf-1-10Mb-Ports.txt
Hostname: jc-mdf-1 Interface: Gi1/0/3 - 10FDx
Writing CR data to CR-data/jc-mdf-2-10Mb-Ports.txt
Hostname: jc-mdf-2 Interface: Gi1/0/5 - 10HDx
Hostname: jc-mdf-2 Interface: Gi1/0/7 - 10HDx
Hostname: jc-mdf-2 Interface: Gi1/0/9 - 10HDx
Writing CR data to CR-data/jc-mdf-3-10Mb-Ports.txt
Hostname: jc-mdf-3 Interface: Gi1/0/48 - 10FDx
No 10Mbps interfaces found for jc-mdf-4
No 10Mbps interfaces found for jc-mdf-cam-1
No 10Mbps interfaces found for jc-mdf-cam-2
Writing CR data to CR-data/lab-3850-10Mb-Ports.txt
Hostname: lab-3850 Interface: Gi1/0/4 - 10HDx
Hostname: lab-3850 Interface: Gi1/0/25 - 10FDx
```

The reason for the script is newer switches with `Smartrate` or `mGig` ports support:
100Mbps
1Gbps
2.5Gbps
5Gbps

I ran into a cutover where the switch had all mGig ports, but most of the devices were all 10Mbps. It was an old parking garage and the OT devices were ancient.

----------------------------------------------------------------

## The ports in use report

Reads ProCurve, Cisco IOS/XE, and Aruba AOS-CX captures. `-interface.json`
carries no vendor field, so the script detects which shape it's looking at
from the keys already in the JSON:

- **ProCurve** has a literal `"total_bytes"` counter per port — the most
  direct signal there is.
- **Cisco IOS/XE**'s `"show interfaces"` has no byte counter at all;
  `"input_packets"`/`"output_packets"` are the closest equivalent, and are
  what's checked and shown for this platform.
- **Aruba AOS-CX** gives separate `rx_total_bytes`/`tx_total_bytes`,
  summed here into one total to match ProCurve's semantics.

Two more vendors are collected but can't answer "is this port in use":
**Cisco S300** falls back to `"show interfaces status"` (its only available
template), which has no traffic-counter field of any kind — a real data
limitation, reported as such rather than guessed at. **Cisco NX-OS** and
**ArubaOS-Switch** have no matching textfsm template for this command in
this project as of this writing, so their captures are unparsed raw text;
`interfaces-in-use.py` detects that case and says so by name too.

This script creates a simple text file with the filename format of hostname-Port-data.txt. For example:

`Procurve-2920-48-Port-data.txt`

The uptime line is read from the same host's own `-system.txt` capture, if
one exists — no `-system.txt`, no uptime line, not an error. Only ports
that have actually passed traffic are listed — a zero-traffic port isn't
shown at all, so "Number of Interfaces with traffic" and the line count
below it always agree; a version that listed every port (zero-traffic ones
included) made the two easy to miscount against each other. Here is a
snippet:

```bash

System Uptime: 3 hours

Number of Interfaces with traffic: 5
Interface 1 - total_bytes 1,510,198
Interface 7 - total_bytes 1,054,112
Interface 12 - total_bytes 842,004
Interface 18 - total_bytes 3,221,905
Interface 24 - total_bytes 12,655
```

## The port migration report

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
