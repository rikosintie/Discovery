#!/usr/bin/env python3
"""
Warm the ARP cache ahead of a port-map run by pinging every host in a set
of subnets.

port-map.py builds its switch-port-to-endpoint map from the ARP tables
collected by config-pull.py, so those tables have to be populated first.
Running this against the customer's user subnets a few minutes before the
discovery pass gives every reachable host an ARP entry on its gateway.

Being gentle on EDR / NDR
-------------------------
Customers increasingly run CrowdStrike, SentinelOne, Darktrace, etc. A
host that fires ICMP at every address in a subnet all at once looks exactly
like a horizontal scan and can get the source machine alerted on or
quarantined. This script defaults to a *paced* sweep:

  * --rate limits how many pings are started per second (default 20).
  * host order within each subnet is shuffled unless --in-order is given.
  * --count controls echoes per host (default 1, which is enough to
    populate an ARP entry).
  * hosts that ignore ICMP are then tried once with a TCP connect to
    port 9100 (--tcp-ports). Printer NICs routinely sleep through ICMP
    but answer TCP; no data is sent, so no print job is queued. Set
    --tcp-ports "" to disable.

--rate 0 restores the old "start everything at once" behaviour.

Input
-----
A text file (default: vlans.txt) with one subnet per line. Two formats are
accepted and may be mixed in the same file:

  * Pasted straight from a switch:

        show run | i ^interface|^ ip address

    interface Vlan10
     ip address 10.20.10.1 255.255.255.0

  * One subnet per line, as "address mask" or CIDR:

        10.20.10.0 255.255.255.0
        10.20.20.0/24

Blank lines, lines containing "interface", and lines starting with "#" are
ignored, so you can comment a subnet out by prefixing it with "#".

Subnets larger than --max-hosts addresses (default 2100, i.e. bigger than a
/21) are skipped.

Usage
-----
    python3 pinger.py
    python3 pinger.py --file user-subnets.txt --rate 10 --count 1
    python3 pinger.py --rate 0 --in-order        # old fast/noisy behaviour
    python3 pinger.py --tcp-ports 9100,9101,9102 # extra printer-server ports
    python3 pinger.py --tcp-ports ""             # ICMP only, no TCP probe
"""

import argparse
import ipaddress
import platform
import random
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def build_ping_command(ip: str, system: str, count: int) -> list[str]:
    """Return the platform-appropriate ``ping`` argv for a single host.

    `count` ICMP echoes, numeric output, with a short overall deadline so a
    dead host does not hold the batch open.
    """
    n = str(count)
    if system == "Windows":
        return ["ping", "-n", n, "-w", "1000", ip]
    if system == "Darwin":
        # macOS: -t is the total timeout in seconds
        return ["ping", "-n", "-c", n, "-t", "4", ip]
    # Linux and everything else: -w is the deadline in seconds
    return ["ping", "-n", "-c", n, "-w", "4", ip]


def host_answered(output: bytes) -> bool:
    """True only if ping received a real ICMP echo reply.

    The exit code alone is not reliable on Windows: when a host in a
    directly-connected subnet does not exist, the local IP stack replies
    "Destination host unreachable", which Windows ping counts as a reply and
    exits 0. A genuine echo reply always carries "TTL=" (Windows) / "ttl="
    (Linux, macOS); the unreachable and timeout messages never do.
    """
    return b"ttl=" in output.lower()


def parse_subnet_line(line: str) -> str | None:
    """Turn one input line into an ``address/mask`` string, or None to skip it.

    Handles both the switch ``ip address <addr> <mask>`` form and a bare
    ``<addr> <mask>`` / ``<addr>/<prefix>`` line.
    """
    line = line.strip()
    if not line or line.startswith("#") or "interface" in line.lower():
        return None

    tokens = line.split()
    if len(tokens) >= 2 and tokens[0] == "ip" and tokens[1] == "address":
        tokens = tokens[2:]

    if len(tokens) == 1:
        return tokens[0]  # already CIDR, e.g. 10.20.10.0/24
    if len(tokens) == 2:
        return f"{tokens[0]}/{tokens[1]}"  # address + mask
    return None


def read_subnets(path: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Read the subnet file and return a list of validated networks."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except FileNotFoundError:
        print(f"{path} does not exist")
        return []

    subnets = []
    for line in lines:
        candidate = parse_subnet_line(line)
        if candidate is None:
            continue
        try:
            subnets.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            print(f"Skipping unrecognized subnet line: {line.strip()!r}")
    return subnets


def tcp_probe(ip: str, ports: list[int], timeout: float) -> int | None:
    """Return the first port in `ports` that accepts a TCP connection.

    The socket is opened and closed straight away with nothing written to
    it: the handshake alone registers the host's MAC on the switch and its
    ARP entry on the gateway, and sending no data means no print job lands
    on port 9100. Returns None if every port refuses, filters, or times
    out.
    """
    for port in ports:
        try:
            with socket.create_connection((ip, port), timeout=timeout):
                return port
        except OSError:
            continue
    return None


def probe_hosts(
    hosts: list[str],
    system: str,
    count: int,
    rate: int,
    tcp_ports: list[int],
    tcp_timeout: float,
) -> dict[str, str]:
    """Warm every host's ARP entry and report how each one answered.

    An ICMP echo pass first, starting at most `rate` pings per second
    (0 = no cap); finished pings are collected as we go so the number of
    open processes stays small even on a large subnet. Every host that
    stays silent is then probed once per port in `tcp_ports` with a
    `tcp_timeout`-second connect, which wakes NICs (printers especially)
    that drop ICMP. Values are "icmp", "tcp/<port>", or "" for no answer.
    """
    interval = 1.0 / rate if rate > 0 else 0.0
    in_flight: dict[str, subprocess.Popen] = {}
    results: dict[str, str] = {}

    def collect(block: bool) -> None:
        for ip in list(in_flight):
            proc = in_flight[ip]
            if not block and proc.poll() is None:
                continue
            output, _ = proc.communicate()
            results[ip] = "icmp" if host_answered(output) else ""
            del in_flight[ip]

    for ip in hosts:
        in_flight[ip] = subprocess.Popen(
            build_ping_command(ip, system, count),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if interval:
            time.sleep(interval)
        collect(block=False)

    collect(block=True)

    pending = [ip for ip, how in results.items() if not how]
    if tcp_ports and pending:
        with ThreadPoolExecutor(max_workers=min(64, len(pending))) as pool:
            futures = {}
            for ip in pending:
                futures[pool.submit(tcp_probe, ip, tcp_ports, tcp_timeout)] = ip
                if interval:
                    time.sleep(interval)
            for future in as_completed(futures):
                port = future.result()
                if port is not None:
                    results[futures[future]] = f"tcp/{port}"

    return results


def ping_subnet(
    subnet,
    system: str,
    max_hosts: int,
    count: int,
    rate: int,
    shuffle: bool,
    tcp_ports: list[int],
    tcp_timeout: float,
) -> None:
    """Probe every usable host in one subnet and print which ones answer."""
    if subnet.num_addresses > max_hosts:
        print(f"Skipped {subnet} ({subnet.num_addresses} addresses > {max_hosts})")
        return

    hosts = [str(host) for host in subnet.hosts()]
    if shuffle:
        random.shuffle(hosts)

    print()
    print(f"Pinging {len(hosts)} hosts in {subnet}")
    results = probe_hosts(hosts, system, count, rate, tcp_ports, tcp_timeout)

    print()
    print("------ Results from the Pings ------")
    for ip in sorted(results, key=ipaddress.ip_address):
        how = results[ip]
        print(f"{ip} {f'active ({how})' if how else 'no response'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ping every host in the subnets listed in a file to warm the ARP cache."
    )
    parser.add_argument(
        "-f", "--file", default="vlans.txt", help="subnet list file (default: vlans.txt)"
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=1,
        help="ICMP echo requests per host (default: 1, which is enough for ARP)",
    )
    parser.add_argument(
        "-r",
        "--rate",
        type=int,
        default=20,
        help="max pings started per second, 0 = no limit (default: 20)",
    )
    parser.add_argument(
        "--in-order",
        action="store_true",
        help="ping hosts low-to-high instead of in random order",
    )
    parser.add_argument(
        "--tcp-ports",
        default="9100",
        help='TCP ports to try on hosts that ignore ICMP, comma-separated '
        '(default: "9100"); pass "" to disable the TCP probe',
    )
    parser.add_argument(
        "--tcp-timeout",
        type=float,
        default=1.0,
        help="seconds to wait for each TCP connection (default: 1.0)",
    )
    parser.add_argument(
        "-m",
        "--max-hosts",
        type=int,
        default=2100,
        help="skip subnets with more addresses than this (default: 2100)",
    )
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.rate < 0:
        parser.error("--rate must be 0 (no limit) or a positive number")
    try:
        tcp_ports = [int(p) for p in args.tcp_ports.split(",") if p.strip()]
    except ValueError:
        parser.error("--tcp-ports must be comma-separated port numbers")
    if any(not 0 < port < 65536 for port in tcp_ports):
        parser.error("--tcp-ports values must be between 1 and 65535")
    if args.tcp_timeout <= 0:
        parser.error("--tcp-timeout must be greater than 0")

    system = platform.system()
    echoes = "1 echo request" if args.count == 1 else f"{args.count} echo requests"
    print()
    print(f"OS is {system}, sending {echoes} per host")
    if args.in_order:
        print("IP addresses pinged in low-to-high order (--in-order)")
    else:
        print("IP addresses have been randomized")
    if tcp_ports:
        joined = ", ".join(str(port) for port in tcp_ports)
        print(f"ICMP non-responders will be TCP-probed on port(s) {joined}")
    else:
        print('TCP probe disabled (--tcp-ports "")')

    subnets = read_subnets(args.file)
    if not subnets:
        print("No subnets to ping.")
        sys.exit(1)

    to_ping = [s for s in subnets if s.num_addresses <= args.max_hosts]
    total_hosts = sum(sum(1 for _ in s.hosts()) for s in to_ping)
    print(f"Number of Subnets: {len(subnets)}")
    if args.rate > 0 and total_hosts:
        print(
            f"{total_hosts} hosts to ping at {args.rate}/s "
            f"(~{total_hosts / args.rate:.0f}s of launches)"
        )

    for subnet in subnets:
        ping_subnet(
            subnet,
            system,
            args.max_hosts,
            args.count,
            args.rate,
            shuffle=not args.in_order,
            tcp_ports=tcp_ports,
            tcp_timeout=args.tcp_timeout,
        )


if __name__ == "__main__":
    main()
