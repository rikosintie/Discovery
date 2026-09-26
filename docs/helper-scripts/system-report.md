# The System Report

`system-report.py` (replacing `procurve-system-report.py`, which only
understood ProCurve) reads `Interface/<host>-system.txt` and writes a
labeled key:value summary per switch — handy for filling out a Change
Request form or a transmittal. Being a plain text file, it's grep-friendly:

`grep -Eir -b4 "serial number" *system-report.txt`

To pull a list of serial numbers from the system reports.

```bash
python3 system-report.py                      # every Interface/*-system.txt
python3 system-report.py -f Interface/2920-system.txt
```

`-system.txt` carries no vendor field, so the script detects which of five
schemas it's looking at from the keys already in the JSON:

- **ProCurve** (`show system information`) is the richest — contact,
  location, CPU/memory, packet counters, in addition to serial/version/MAC.
- **Cisco IOS/XE** (`show version`) gives hostname, one combined uptime
  string, and hardware model/serial/MAC as lists (a stack reports one of
  each per member — joined with commas here).
- **Cisco NX-OS** (`show version`) gives hostname, uptime, platform,
  serial, and the last reboot reason.
- **Cisco S300** (`show version`) is the sparsest of all — only
  software/boot/hardware version. No hostname, serial, or uptime field
  exists in that command's output at all; the hostname shown falls back to
  the capture's filename.
- **Aruba AOS-CX** (`show system`) gives hostname, contact/location,
  vendor/product, serial, MAC, version, and uptime as separate
  weeks/days/hours/minutes fields (no combined string, unlike the Cisco
  platforms — assembled into one line here).

`config-pull.py` runs the matching command for every vendor above.
`aruba_osswitch` (ArubaOS-Switch) is the one exception — no `show
version`/`show system` textfsm template exists for it anywhere in this
project, so its capture stays unparsed raw text. `system-report.py`
detects that case and says so by name instead of guessing at a format
nobody has captured, or crashing on a missing key.

Real output from a mixed-vendor sweep — ProCurve and a Cisco IOS-XE 3850
side by side, one run:

```bash
python3 system-report.py
Writing system report for 2920 to
 Interface/neighbors/2920-system-report.txt
        Hostname: HP-2920-24G-PoEP
   snmp location: Garage
    snmp contact: Michael Hubbard
 MAC address age: 300
        timezone: -480
   daylight_rule: Continental-US-and-Canada
software_version: WB.16.10.0025
     rom_version: WB.16.03
     mac address: 98f2b3-fe8880
   serial number: SG78FLXH0B
   system_uptime: 243 days
 cpu_utilization: 47
        mem_free: 39,545,240

Writing system report for lab-3850 to
 Interface/neighbors/lab-3850-system-report.txt
        Hostname: LAB_3850
software_version: 16.12.3a
  software_image: CAT3K_CAA-UNIVERSALK9-M
        hardware: WS-C3850-48U
     mac address: f8:7b:20:34:a3:80
   serial number: FOC2134U131
   system_uptime: 45 weeks, 1 day, 3 hours, 35 minutes
   reload_reason: Power Failure or Unknown
 config_register: 0x102
```

The report is written to `Interface/neighbors/<host>-system-report.txt`,
same as before.
