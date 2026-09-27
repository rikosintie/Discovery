# Warming the ARP cache with pinger.py

----------------------------------------------------------------

![tux-pinger](img/tux-pinger.JPG)

----------------------------------------------------------------

The port maps are only as complete as the ARP tables `config-pull.py`
collects, and a switch only has an ARP entry for a host that has sent
traffic recently. `pinger.py` reads a list of subnets and pings every host
in them so the gateways learn all the endpoints before the discovery run.

Put the subnets in a file (default `vlans.txt`), one per line. You can
paste straight into a Cisco switch:

```text
show run | i ^interface Vlan|^ ip address
```

```bash title="Cisco IOS interfaces"
LAB_3850#show run | i ^interface Vlan|^ ip address
 ip address 10.10.10.10 255.255.255.255
interface Vlan1
interface Vlan10
 ip address 192.168.10.253 255.255.255.0
interface Vlan11
 ip address 192.168.1.1 255.255.255.0
interface Vlan12
 ip address 192.168.12.1 255.255.255.0
interface Vlan20
 ip address 10.1.20.1 255.255.255.0
interface Vlan30
 ip address 10.1.30.1 255.255.255.0
```

----------------------------------------------------------------

On an HPE Procurve:

```unixconfig linenums='1' hl_lines='1'
show running-config | include "^vlan|^   ip address"
```

```unixconfig title='Procurve interfaces'
vlan 1
   ip address dhcp-bootp
vlan 10
   ip address 192.168.10.52 255.255.255.0
vlan 20
   ip address 10.164.24.200 255.255.255.0
   ip address 10.10.100.1 255.255.255.0
vlan 850
   ip address 10.254.34.18 255.255.255.252
```

----------------------------------------------------------------

— or list them as `address mask` or CIDR:

```text
10.20.10.0 255.255.255.0
10.20.20.0/24
10.10.10.11/32
```

----------------------------------------------------------------

Blank lines, lines containing `interface`, and lines starting with `#` are
ignored, so `#` comments a subnet out. Subnets larger than `-m/--max-hosts`
addresses (default 2100, i.e. bigger than a `/21`) are skipped.

```bash title="pinger.py example"
python3 pinger.py # no options - use vlans.txt, -c =1, -r =20
python3 pinger.py -f user-subnets.txt # custom address file
```

----------------------------------------------------------------

## Command-line options

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

----------------------------------------------------------------

## Cross-platform examples

=== "Linux"

    ```text
    python3 pinger.py

    OS is Linux, sending 1 echo request per host
    IP addresses have been randomized
    Number of Subnets: 3
    90 hosts to ping at 20/s (~4s of launches)

    Pinging 30 hosts in 192.168.10.96/27
    ```

=== "macOS"

    ```text
    python3 pinger.py

    OS is Darwin, sending 1 echo request per host
    IP addresses have been randomized
    Number of Subnets: 3
    90 hosts to ping at 20/s (~4s of launches)

    Pinging 30 hosts in 192.168.10.96/27
    ```

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

## Which subnets are worth pinging

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

----------------------------------------------------------------

## How it works

`pinger.py` runs two passes over the host list:

1. **Paced ICMP sweep** — one echo request per host by default, in randomized order,
   started at no more than `--rate` per second so the traffic reads as
   background noise rather than a horizontal scan.
2. **TCP fallback** — every host that stayed silent on ICMP gets one TCP
   connect to port 9100 (`--tcp-ports`), opened and closed with nothing
   written to it. This catches hosts that are link-up and answering ARP but
   drop ICMP: host firewalls, and printer NICs whose firmware answers ARP but
   ignores echo. A refused connection (TCP RST) counts as alive — the RST
   still proves the host is up and has just refreshed its MAC on the switch
   and its ARP entry on the core.

Each host prints as `active (icmp)`, `active (tcp/9100)`, `active (rst/9100)`,
or `None`.

----------------------------------------------------------------

**What it can't reach.** A host that is fully asleep with its switch port down
is unreachable by any probe — ICMP, TCP, or ARP — until the port comes back
up. The TCP fallback only helps hosts that are still on the wire.

**Run it off-subnet.** With an L3 core holding an SVI for every user subnet,
run `pinger.py` from a host that reaches those subnets *through* the core. The
core resolves each target itself to forward the packet and installs the ARP
entry, which is what `config-pull.py` later collects. A same-subnet run only
refreshes the local access switch's CAM table and never touches the core's ARP
table.

**Why the timing matters.** Cisco's default ARP timeout (4 hours, HPE Procurve 20 minutes), outlives its CAM
aging (5 min), so the core can list an ARP entry for a host whose
access-switch port has already aged out of the CAM table — and `port-map.py`
needs both. Running `pinger.py` a few minutes before the discovery pass
refreshes both at once.

----------------------------------------------------------------

## Being gentle on EDR / NDR

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

At Fal.Con 2026 I walked a CrowdStrike engineer (Jeff) through how `pinger.py`
works. His assessment was that the Falcon sensor on endpoints should not flag
the paced sweep. A later run at a customer with `vlans.txt` set to
`10.100.126.0/24` produced no CrowdStrike alerts.

----------------------------------------------------------------

Here is an example from a recent engagement at a customer running CrowdStrike Falcon:

```text linenums='1' hl_lines='1'
python3 pinger.py -f vlans.txt --tcp-ports 9100

OS is Linux, sending 1 echo request per host
IP addresses have been randomized
ICMP non-responders will be TCP-probed on port(s) 9100
Number of Subnets: 2
316 hosts to ping at 20/s (~16s of launches)

Pinging 62 hosts in 172.20.126.0/26

------ Results from the Pings ------
172.20.126.1 no response
172.20.126.2 active (icmp)
172.20.126.3 active (icmp)
172.20.126.4 active (icmp)

... Truncated for brevity

Pinging 254 hosts in 10.100.126.0/24

------ Results from the Pings ------
10.100.126.1 active (icmp)
10.100.126.2 no response
10.100.126.3 no response
10.100.126.4 no response
10.100.126.5 active (icmp)
10.100.126.6 active (icmp)
```

----------------------------------------------------------------

The `------ Results from the Pings ------` output above looks sequential,
but that's just for readability — the pings themselves were still sent in
randomized order (confirmed with a Wireshark capture on this exact run).
The script shuffles the send order before pinging, then always re-sorts the
*printed* results back into ascending IP order afterward, so the two are
independent: the traffic on the wire is randomized, the report you read is
sorted.

----------------------------------------------------------------

## Waking sleeping printers

Printers are the hardest devices to get an ARP entry for: their NICs drop
into a deep sleep and ignore ICMP echo, so even `-c 3` often comes back
empty. Almost every network printer, though, keeps TCP port 9100 (RAW /
JetDirect / AppSocket) open, and a bare TCP handshake to an open port
wakes the NIC where a ping will not.

After the ICMP pass, `pinger.py` opens one TCP connection to port 9100 on
every host that stayed silent and closes it immediately. Nothing is
written to the socket, so nothing prints. A host woken this way is
reported as `active (tcp/9100)`, or `active (rst/9100)` if it refused the
connection — either way the NIC is awake and its MAC is back on the switch.

- **`--tcp-ports`** — comma-separated ports to try (default `9100`). Add
  `9101,9102` for multi-port external print servers. Pass `--tcp-ports ""`
  to switch the TCP probe off and go back to ICMP only.
- **`--tcp-timeout`** — seconds to wait for each connection (default
  `1.0`).

```text
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

Swap in the printer's address. It prints `tcp/9100` if the handshake
completed, or `rst/9100` if the printer refused the connection — either way
the NIC is awake and its MAC is back on the switch — or `None` if nothing
answered on that port within a second. Nothing is sent to the printer, so no
page comes out.

**Or list every printer as a `/32`.** To wake a known set of printers on a
normal run without touching the rest of the subnet, put each one in
`vlans.txt` as a single-host entry:

```text
ip address 192.168.10.109/32
ip address 192.168.10.110/32
```

`pinger.py` expands a `/32` to just that one address, so the run hits
exactly the printers you listed.
