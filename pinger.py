#!/usr/bin/env python3
"""
Warm the ARP cache ahead of a port-map run by pinging every host in a set
of subnets.

port-map.py builds its switch-port-to-endpoint map from the ARP tables
collected by config-pull.py, so those tables have to be populated first.
Running this against the customer's user subnets a few minutes before the
discovery pass gives every reachable host an ARP entry on its gateway.

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
/21) are skipped: firing thousands of ping processes at once is unreliable.

Usage
-----
    python3 pinger.py
    python3 pinger.py --file user-subnets.txt --max-hosts 4100
"""

import argparse
import ipaddress
import platform
import subprocess
import sys


def build_ping_command(ip: str, system: str) -> list[str]:
    """Return the platform-appropriate ``ping`` argv for a single host.

    Three ICMP echoes, numeric output, with a short overall deadline so a
    dead host does not hold the batch open.
    """
    if system == "Windows":
        return ["ping", "-n", "3", "-w", "1000", ip]
    if system == "Darwin":
        # macOS: -t is the total timeout in seconds
        return ["ping", "-n", "-c", "3", "-t", "4", ip]
    # Linux and everything else: -w is the deadline in seconds
    return ["ping", "-n", "-c", "3", "-w", "4", ip]


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


def ping_subnet(subnet, system: str, max_hosts: int) -> None:
    """Ping every usable host in one subnet and print which ones answer."""
    if subnet.num_addresses > max_hosts:
        print(f"Skipped {subnet} ({subnet.num_addresses} addresses > {max_hosts})")
        return

    print()
    print(f"Pinging hosts in {subnet}")
    procs = {
        str(host): subprocess.Popen(
            build_ping_command(str(host), system),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for host in subnet.hosts()
    }

    print()
    print("------ Results from the Pings ------")
    # Every ping is already running; just collect them in address order.
    for ip, proc in procs.items():
        if proc.wait() == 0:
            print(f"{ip} active")
        else:
            print(f"{ip} no response")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ping every host in the subnets listed in a file to warm the ARP cache."
    )
    parser.add_argument(
        "-f", "--file", default="vlans.txt", help="subnet list file (default: vlans.txt)"
    )
    parser.add_argument(
        "-m",
        "--max-hosts",
        type=int,
        default=2100,
        help="skip subnets with more addresses than this (default: 2100)",
    )
    args = parser.parse_args()

    system = platform.system()
    print()
    print(f"OS is {system}")

    subnets = read_subnets(args.file)
    if not subnets:
        print("No subnets to ping.")
        sys.exit(1)

    print(f"Number of Subnets: {len(subnets)}")
    for subnet in subnets:
        ping_subnet(subnet, system, args.max_hosts)


if __name__ == "__main__":
    main()
