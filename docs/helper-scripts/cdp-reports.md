# CDP Neighbor Reports

----------------------------------------------------------------

![Tux-cdp-neighbor](img/tux-cdp1.jpeg)

----------------------------------------------------------------

CDP (Cisco Discovery Protocol) is Cisco-proprietary, but HP ProCurve speaks
it too. Juniper (JunOS) and Brocade/Ruckus FastIron don't — they're
LLDP-only, see [LLDP Neighbor Reports](lldp-reports.md) for those. Of the
platforms Discovery supports, CDP neighbor data is only ever available from
Cisco IOS/IOS-XE/NX-OS and HP ProCurve.

## cdp-ne.py

`cdp-ne.py` reads the JSON `config-pull.py` already wrote to
`Interface/<host>-cdp.txt` and prints a `port-map.py`-styled table:

```bash
python3 cdp-ne.py                        # every Interface/*-cdp.txt
python3 cdp-ne.py -f Interface/jc-mdf-1-cdp.txt
python3 cdp-ne.py -d 10.100.126.9        # PTR lookups via that server
python3 cdp-ne.py --no-dns               # skip PTR lookups
python3 cdp-ne.py --csv                  # also write a .csv report
```

No entries, or fewer than expected? CDP has to be turned on per-switch first
— see [Enabling CDP](#enabling-cdp) below.

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

The report is also written to `Interface/neighbors/<host>-cdp-ne.txt`, and,
with `--csv`, to `Interface/neighbors/<host>-cdp-ne.csv` — handy for sorting
or filtering the results in a spreadsheet or the Rainbow CSV extension.

## Enabling CDP

### Cisco IOS

CDP is on by default — it just won't show in `show run` on a factory-default
switch, since that only prints lines that differ from the default. The
defaults themselves show up with `show run all`:

```bash
Switch# show run all | i cdp
cdp advertise-v2
cdp timer 60
cdp holdtime 180
cdp log mismatch duplex
cdp run
```

Confirm it's active, and see per-port status, with:

```bash
Switch# show cdp
```

To turn it off on a specific port (for example, one facing an ISP or
extranet partner):

```bash
Switch(config)# interface GigabitEthernet1/0/24
Switch(config-if)# no cdp enable
```

And globally, if it's ever been turned off:

```bash
Switch(config)# cdp run
```

### HP ProCurve

Off by default; turn it on globally:

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

The exception is for ports that connect to external entities such as an ISP or extranet partner. I do not recommend every enabling `CDP` on a port connected to an ISP.

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
