"""
!!!!! Discovery Script - Does not change the running config !!!!!

Reference
https://github.com/rikosintie/Discovery
https://pynet.twb-tech.com/blog/netmiko-read-timeout.html
https://stackoverflow.com/questions/9539921/how-do-i-define-a-function-with-optional-arguments
ntc templates are located at Discovery/lib/python3.11/site-packages/ntc_templates/templates
https://pynet.twb-tech.com/blog/netmiko-and-textfsm.html

Usage
1. Clone the repo at https://github.com/rikosintie/Discovery/. The readme file
in the repo detailed installation instructions.

2. Create a file named device-inventory-<site>.
Example
device-inventory-test
Place the information for each switch in the file. Format is
<IP Address>,hp_procurve,<hostname>,<username>
Example
192.168.10.52,hp_procurve,gl-IDF1,mhubbard
NOTE: the password is saved in user environment variable or entered when the script
is executed.

3. Create a file named <vendor_id>-config-file.txt in teh root of the Discovery
folder. Place the configuration commands for the switches in it. Note that
there are default files included. You can customize it to suit your needs.
Valid config file names are:
    hp_procurve-config-file.txt is used for all HP Procurve switches
    cisco_ios-config-file.txt is used for all Cisco IOS switches
    cisco_xe-config-file.txt is used for all Cisco IOS XE switches
    cisco_nxos-config-file.txt is used for all Cisco NXOS switches
    aruba_osswitch-config-file.txt is used for all Aruba OS switches
    aruba_cx-config-file.txt is used for all Aruba CX switches

4. Execute
python3 cisco-Config-Pull.py -s test

The script will read the device-inventory-<sitename> file and
execute the contents of the <hostname>-config-file.txt for each switch.

For each switch in the inventory file the commands that were
sent to the switch are saved to the CR-data folder as <hostname>-CR-data.txt.

The script will also create file with a show running configuration in the Running
folder called <hostname>-running-config.txt

---Error Handling ---
The connect handler is wrapped in a try/except block.
If a time out occurs when connecting to a switch it is trapped, a message is
displayed and the script moves to the next switch.
"""

# !!!!! Discovery Script - Does not change the running config !!!!!
import argparse
import csv
import getpass
import json
import logging
import os
import re
import socket
import sys
import timeit
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, TypedDict

from icecream import ic
from netmiko import ConnectHandler
from netmiko.exceptions import AuthenticationException, NetmikoTimeoutException
from paramiko.ssh_exception import SSHException
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# !!!!! Discovery Script - Does not change the running config !!!!!

__author__ = "Michael Hubbard"
__author_email__ = "michael.hubbard999@gmail.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
#  cisco_Config_Pull.py
#  Procurve Change Request data collection
#  Created by Michael Hubbard on 2023-12-20.

# comment out ic.disable() and uncomment ic.enable() to use icecream
# ic.enable()
ic.disable()


class SkippedDevice(TypedDict):
    hostname: str
    ip: str
    reason: str


console = Console()


def create_filename(sub_dir1: str, extension: str = "", sub_dir2: str = "") -> str:
    """
    returns a valid path regardless of the OS

    Args:
        sub_dir1 (str): name of the sub directory off the cwd required
        extension (str): string appended after hostname - ex. -interface.txt
        sub_dir2 (str, optional): if a nested sub_dir is used Defaults to "".

    Returns:
        str: full pathname of the file to be written
    """
    current_path = os.getcwd()
    extension = hostname + extension
    int_report = os.path.join(current_path, sub_dir1, sub_dir2, extension)
    return int_report


def remove_empty_lines(filename: str) -> None:
    """
    Removes empty lines from the file. The fabric loop will fail if there
    empty lines in the csv file.

    Args:
        filename (str): File in the current working directory to be opened.

    Returns:
        None - the updated file is written to disk.
    """
    if not os.path.isfile(filename):
        print(f"{filename} does not exist.")
        return

    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w") as filehandle:
        lines = list(filter(lambda x: x.strip(), lines))
        filehandle.writelines(lines)


# function to return vendor specific commands and flags
def which_vendor(vendor: str) -> Tuple[str, str, str, str, bool]:
    """
    Returns vendor-specific command strings, JSON interface key, and prefix behavior.

    Args:
        vendor (str): Vendor ID string.

    Returns:
        Tuple[str, str, str, str, bool]: Commands and flags:
            - show_run
            - show_lldp
            - show_arp
            - interface_key
            - force_prefix: whether to prepend GigabitEthernet to interfaces like "1/1/1"
    """
    vendor = vendor.lower()
    match vendor:
        case "hp_procurve":
            return (
                "show running structured",
                "show lldp info remote detail",
                "show arp",
                "port",
                True,
            )
        case "aruba_osswitch":
            return (
                "show running",
                "show lldp neighbor-info detail",
                "show arp",
                "interface",
                True,
            )
        case "aruba_cx":
            return (
                "show running-config",
                "show lldp neighbors detail",
                "show arp",
                "interface",
                False,
            )
        case "cisco_ios" | "cisco_xe":
            return (
                "show running",
                "show lldp neighbor detail",
                "show ip arp",
                "interface",
                True,
            )
        case "cisco_nxos":
            return (
                "show running-config",
                "show lldp neighbors detail",
                "show ip arp",
                "interface",
                False,
            )
        case _:
            raise ValueError(f"Unsupported vendor: {vendor}")

    return sh_run, show_lldp, show_arp, interface_key


# function to create a "show mac address table file by reading the interface
# JSON file.
def generate_mac_query_file_from_json(
    json_file_path: str,
    output_file_path: str,
    interface_key: str = "interface",
    force_prefix: bool = True,
) -> None:
    """
    Reads a JSON file containing interface data and generates a configuration
    file with 'show mac address-table interface ... | i XX' commands for each
    valid interface.

    Args:
        json_file_path (str): Path to the JSON file containing interface data.
        output_file_path (str): Path to the output text file where commands will be written.
        interface_key (str): The key in the JSON dict that holds interface names.
        force_prefix (bool): If True, prepends 'GigabitEthernet' to bare interfaces like '1/0/1'.

    Raises:
        FileNotFoundError: If the specified JSON file does not exist.
        ValueError: If no valid interface names are found in the JSON file.
    """

    if not os.path.isfile(json_file_path):
        raise FileNotFoundError(f"JSON file not found: {json_file_path}")

    with open(json_file_path, "r") as file:
        try:
            interface_data = json.load(file)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    commands: list[str] = []

    for entry in interface_data:
        intf_name = entry.get(interface_key)
        # Skip VLAN interfaces (they can't be used in 'show mac address-table interface' queries)
        if intf_name.lower().startswith("vlan"):
            continue
        if intf_name.lower().startswith("lo"):
            continue
        if intf_name.lower().startswith("tu"):
            continue
        if not intf_name:
            continue

        # Conditionally normalize interface names
        if force_prefix and re.match(r"^\d+/\d+/\d+$", intf_name):
            intf_name = f"GigabitEthernet{intf_name}"

        # Extract interface type abbreviation for grep
        match = re.match(r"([A-Za-z]+)", intf_name)
        if match:
            abbrev = match.group(1)[:2]
        else:
            abbrev = intf_name.split("/")[0]

        # cmd = f"show mac address-table interface {intf_name} | i {abbrev}"
        # cmd = f"{maddr} {intf_name} | i {abbrev}"

        cmd = f"{maddr} {intf_name}"
        commands.append(cmd)

    if not commands:
        raise ValueError("No valid interfaces found in the JSON file.")

    with open(output_file_path, "w") as f:
        f.write("\n".join(commands))

    print(f"Writing {len(commands)} '{maddr}' commands to\n {output_file_path}")


def print_panel(
    message: str,
    title: str = "",
    subtitle: str = "",
    border_style: str = "cyan",
    expand: bool = False,
    title_emoji: str = "",
) -> None:
    """
    Print a rich-styled panel message.

    Args:
        message (str): The message body (Rich markup supported).
        title (str): Optional title displayed at the top of the panel.
        subtitle (str): Optional subtitle displayed at the bottom.
        border_style (str): Color/style of the panel border (default: "cyan").
        expand (bool): Whether to expand to full width of terminal.
        title_emoji (str): Emoji prefix for title (e.g., "\u26a0\ufe0f", "\u2705").
    """
    if title_emoji:
        title = f"{title_emoji} {title}"
    print(
        Panel.fit(message, title=title, subtitle=subtitle, border_style=border_style)
        if not expand
        else Panel(message, title=title, subtitle=subtitle, border_style=border_style)
    )


def emoji_for(label: str) -> str:
    label = label.lower()
    mapping = {
        "saving": "\U0001f4be",  # 💾
        "success": "\u2705",  # ✅
        "error": "\u274c",  # ❌
        "warning": "\u26a0\ufe0f",  # ⚠️
        "info": "\u2139\ufe0f",  # ℹ️
        "timeout": "\u23f1\ufe0f",  # ⏱️
        "connecting": "\U0001f50c",  # 🔌
        "search": "\U0001f50d",  # 🔍
        "network": "\U0001f310",  # 🌐
        "firewall": "\U0001f525",  # 🔥
        "dns": "\U0001f3f7\ufe0f",  # 🏷️
        "boot": "\U0001f680",  # 🚀
        "shutdown": "\u23fb",  # ⏻
        "build": "\U0001f6e0\ufe0f",  # 🛠️
        "processing": "\U0001f501",  # 🔄
    }
    return mapping.get(label, "")


def print_times() -> None:
    """
    Print combined execution timing information for the current host and total runtime.

    Calculates:
      - The elapsed time for the current host using `timeit.default_timer() - timeit_start`
      - The total script runtime using `timeit.default_timer() - start`

    Outputs both durations in a single styled rich Panel.
    Requires `hostname`, `timeit_start`, and `start` to be defined in the calling scope.
    """
    stop_time = timeit.default_timer()
    host_runtime = stop_time - timeit_start
    total_runtime = stop_time - start

    # Format host time
    mins, secs = divmod(host_runtime, 60)
    hours, mins = divmod(mins, 60)
    host_time_str = f"[bold]{int(hours)}h {int(mins)}m {round(secs, 2)}s[/bold]"

    # Format total time
    mins, secs = divmod(total_runtime, 60)
    hours, mins = divmod(mins, 60)
    total_time_str = f"[bold]{int(hours)}h {int(mins)}m {round(secs, 2)}s[/bold]"

    # Combined message
    message = (
        f"[cyan]{hostname}[/cyan] execution time: {host_time_str}\n"
        f"[blue]Total script runtime:[/blue] {total_time_str}"
    )

    print(Panel.fit(message, border_style="green", title="Execution Timing Summary"))


def log_message(message: str, context: str = "") -> None:
    """
    Append a plain-text message with timestamp to the logfile.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now}] {context + ': ' if context else ''}{message}\n"
    with open(LOGFILE, "a") as f:
        f.write(log_entry)


def strip_rich_markup(message: str) -> str:
    """
    Remove rich markup tags like [red], [bold] from log output.
    """
    import re

    return re.sub(r"\[/?[^\]]+\]", "", message)


def detect_ssh_version(ip: str, port: int = 22, timeout: int = 5) -> str | None:
    """
    Attempt to retrieve the SSH version banner from a device.

    Args:
        ip (str): IP address of the target device
        port (int): SSH port (default 22)
        timeout (int): Timeout in seconds

    Returns:
        str | None: The SSH version banner (e.g. "SSH-2.0-OpenSSH_9.9") or None if failed
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            banner = sock.recv(1024).decode("utf-8", errors="ignore").strip()
            if banner.startswith("SSH-"):
                return banner
    except (socket.timeout, ConnectionRefusedError, OSError):
        return None
    return None


# def write_skipped_devices_csv(filename: str = "skipped_devices.csv") -> None:
def write_skipped_devices_csv(filename: str) -> None:
    if not skipped_devices:
        return
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Hostname", "IP Address", "Reason"])
        for entry in skipped_devices:
            writer.writerow([entry["hostname"], entry["ip"], entry["reason"]])


def print_skipped_devices_table(skipped: list[dict]) -> None:
    """
    Prints a rich table of skipped devices grouped by reason and sorted by IP address.
    Args:
    skipped (list[dict]): List of skipped device entries, each with 'hostname', 'ip', and 'reason'.
    """

    if not skipped:
        return

    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in skipped:
        grouped[entry["reason"]].append(entry)

    for reason, entries in grouped.items():
        table = Table(
            title=f"Skipped Devices — {reason}",
            title_style="bold red",
            header_style="bold magenta",
        )

        table.add_column("Hostname", style="cyan", no_wrap=True)
        table.add_column("IP Address", style="green")

        # Sort by IP address
        entries.sort(key=lambda d: tuple(int(part) for part in d["ip"].split(".")))

        for entry in entries:
            table.add_row(entry["hostname"], entry["ip"])

        console.print(table)
        console.print()  # Add spacing between tables


# ---------------
print()
print()
start = timeit.default_timer()
now = datetime.now()
print(f"Script started at: {now.strftime('%m/%d/%Y, %H:%M:%S')}")
print()
parser = argparse.ArgumentParser(
    description="-s site, -c config-file to use, -l 1 create ssh_log.txt, -p 1 prompt for password, -t 1-9 timeout, -e W,I,M,D,E (-e 1 for Cisco) to pull logs"
)
parser.add_argument(
    "-c",
    "--conf",  # Optional (but recommended) long version
    default="",
    help="config-file to use",
)
parser.add_argument(
    "-e",
    "--event",  # Optional (but recommended) long version
    default="",
    help="-e W,I,M,D,E to pull switch logs, -e 1 for Cisco",
)
parser.add_argument(
    "-l",
    "--logging",  # Optional (but recommended) long version
    default="",
    help="use -l 1 to enable ssh logging",
)
parser.add_argument(
    "-p",
    "--password",  # Optional (but recommended) long version
    default="",
    help="use -p 1 to be prompted for password",
)
parser.add_argument("-s", "--site", help="Site name - ex. HQ")
parser.add_argument(
    "-t",
    "--timeout",  # Optional (but recommended) long version
    default="1",
    help="use -t 1-9 to set timeout",
)
args = parser.parse_args()
site = args.site

# if -l 1 is passed, turn on logging
if args.logging != "":
    #  log all reads and writes on the SSH channel
    logging.basicConfig(filename="ssh_log.txt", level=logging.DEBUG)
    logger = logging.getLogger("netmiko")

# Check for the password, exit if it doesn't exist
password: Optional[str] = ""
if args.password != "":
    password = getpass.getpass(prompt="Input the Password:")
elif os.environ.get("cyberARK"):
    password = os.environ.get("cyberARK")
else:
    print("\n" * 2)
    message = (
        "\n"
        "No password was found. Use:\n\n"
        "[red]python config_pull.py -s site -p 1[/red]\n\n"
        "on the terminal to be prompted for a password,\n"
        "or set the environment variable: \n\n"
        "export [blue]cyberARK=your_password[/blue]\n\n"
        "on the terminal"
        "\n"
    )

    print_panel(
        message,
        title="Password Missing",
        subtitle="A password is required to run this script",
        border_style="red",
        title_emoji=emoji_for("error"),
        expand=False,
    )
    print("\n" * 2)
    sys.exit()

if site is None:
    print("-s site name is a required argument")
    sys.exit()
else:
    dev_inv_file = "device-inventory-" + site + ".csv"

# check if site's device inventory file exists
if not os.path.isfile(dev_inv_file):
    print("{} doesn't exist ".format(dev_inv_file))
    sys.exit()

remove_empty_lines(dev_inv_file)

# u'\ufeff' in Python string When reading from csv files occasionally I got this at the front of the IP address value.
# https://stackoverflow.com/questions/17912307/u-ufeff-in-python-string

with open(dev_inv_file, encoding="utf-8-sig") as devices_file:
    fabric = devices_file.readlines()
    num_devices = len(fabric)

border = "-" * (len(dev_inv_file) + 23)
print(f"[bold][blue]{border}[/blue][/bold]")
# print(f"Reading devices from: {dev_inv_file}")
border = f"Reading devices from: [cyan]{dev_inv_file}[/cyan]"

print(border)
border = "-" * (len(dev_inv_file) + 23)
print(f"[bold][blue]{border}[/blue][/bold]")
print()

# uptime: list[str] = []
skipped_devices: list[dict] = []
device_count: int = 0
time_out_count: int = 0
auth_fail_count: int = 0
connection_fail_count: int = 0
sshv1_skip_count = 0
# skipped_devices: list[tuple[str, str, str]] = []  # hostname, ip, reason

for line in fabric:
    device_count += 1
    line = line.strip("\n")
    ipaddr = line.split(",")[0]
    vendor = line.split(",")[1]
    hostname = line.split(",")[2]
    username = line.split(",")[3]
    maddr = line.split(",")[4]
    if maddr == "":
        # Show the input prompt using rich formatting
        print(
            Panel.fit(
                f"[yellow]show mac address entry is missing in [cyan]device-inventory-{site}.csv[/cyan] for [bold]{hostname}[/bold].[/yellow]\n\n"
                f"[green]Enter 1[/green] to use [bold]'show mac-address'[/bold]\n"
                f"[green]Enter 2[/green] to use [bold]'show mac address-table interface'[/bold]",
                title="⚠ Missing Value",
                border_style="red",
            )
        )

        # Prompt the user for input (plain input, no styling inside input() itself)
        choice = input("Enter 1 or 2: ")

        # Apply their selection
        if choice == "1":
            # Procurve uses 'show mac-address'
            maddr = "show mac-address"
        elif choice == "2":
            # Newer Cisco and other vendors use 'show mac address-table interface'
            maddr = "show mac address-table interface"
        else:
            maddr = "show mac address-table interface"  # fallback
            print(
                "[red]Invalid choice. Defaulting to 'show mac address-table interface'[/red]"
            )

        # Show confirmation
        print(
            Panel(
                f"[bold]Using:[/bold] [green]{maddr}[/green] for [yellow]{hostname}[/yellow]",
                border_style="green",
            )
        )

    sh_run, show_lldp, show_arp, interface_key, force_prefix = which_vendor(vendor)
    ic(sh_run, show_lldp, show_arp, interface_key, force_prefix)
    timeit_start: float = timeit.default_timer()
    start_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    LOGFILE = create_filename("Failure-Logs", "-failure.txt")
    # print("-----------------------------------------------------")
    border = "-" * (len(hostname) + 42)
    print(f"[bold][blue]{border}[/blue][/bold]")
    border = f"[bold][blue]{start_time}[/blue][/bold] Connecting to switch [cyan]{hostname}[/cyan]"
    print(f"{border}")
    border = "-" * (len(hostname) + 42)
    print(f"[bold][blue]{border}[/blue][/bold]")
    # this exposes the paramiko logging module so that the timeout exception
    # can catch ssh v1, v1.5 mismatch errors.
    logging.getLogger("paramiko").setLevel(logging.CRITICAL)
    try:
        device = {
            "device_type": vendor,
            "ip": ipaddr,
            "username": username,
            "password": password,
            "conn_timeout": 60,
        }
        # 🔍 Check SSH version before attempting connection
        banner = detect_ssh_version(ipaddr)
        if banner:
            if banner.startswith("SSH-1."):
                # Legacy SSHv1 — not supported
                sshv1_skip_count += 1
                skipped_devices.append(
                    {"hostname": hostname, "ip": ipaddr, "reason": "SSHv1 only"}
                )

                message = (
                    f"[red]Unsupported SSH version[/red]: {banner}\n"
                    f"This device only supports SSHv1 and cannot be accessed by this tool.\n"
                    f"Use console or PuTTY if needed."
                )
                print(
                    Panel.fit(
                        message,
                        title="🔐 SSHv1 Detected",
                        border_style="red",
                        subtitle=f"Skipping {hostname}",
                    )
                )
                log_message(strip_rich_markup(message))
                device_count -= 1
                continue
            elif banner.startswith("SSH-1.99"):
                # SSH-1.99 is a hybrid banner — usually safe for SSHv2
                pass  # Let ConnectHandler try
            # else: SSH-2.0 — fully supported
        else:
            # No banner received — might not be an SSH server at all
            message = (
                f"[yellow]No SSH banner received[/yellow] from {ipaddr}\n"
                f"Unable to determine SSH compatibility.\nSkipping to avoid hang."
            )
            print(
                Panel.fit(
                    message,
                    title="⚠️ No SSH Response",
                    border_style="yellow",
                    subtitle=f"Skipping {hostname}",
                )
            )
            log_message(strip_rich_markup(message))
            device_count -= 1
            connection_fail_count += 1
            skipped_devices.append(
                {"hostname": hostname, "ip": ipaddr, "reason": "No SSH banner received"}
            )
            continue

        # ✅ Now try connecting
        net_connect = ConnectHandler(**device)

    except NetmikoTimeoutException as e:
        end_time: datetime = datetime.now()
        device_count -= 1
        time_out_count += 1
        skipped_devices.append(
            {"hostname": hostname, "ip": ipaddr, "reason": "Timeout connecting"}
        )
        # Improved message with underlying exception
        message = (
            f"Could not connect to {hostname} at {ipaddr}.\n"
            f"[red]The connection timed out.[/red]"
        )
        if "Protocol major versions differ" in str(e):
            message += (
                f"\n[bold yellow]Warning:[/bold yellow] SSH version mismatch detected on {hostname}."
                f"\nDevice may only support SSHv1 (deprecated on modern Linux)"
            )
        else:
            message += f"\n[dim]{str(e)}[/dim]"

        print(
            Panel.fit(
                message,
                title="⚠️ Timeout",
                border_style="yellow",
                subtitle=f"Timeout connecting to {hostname}",
            )
        )
        log_message(strip_rich_markup(message))
        remove_empty_lines(LOGFILE)
        print()
        print_times()
        continue

    except AuthenticationException:
        auth_fail_count += 1
        device_count -= 1
        skipped_devices.append(
            {"hostname": hostname, "ip": ipaddr, "reason": "Authentication failed"}
        )
        message = f"Could not connect to {hostname} at {ipaddr}. \n[red]The Credentials failed.[/red] \nRemove [cyan]{hostname}[/cyan] from the device inventory file"
        print(
            Panel.fit(
                message,
                title="⚠️ Credentials",
                border_style="yellow",
                subtitle=f"Missing credentials {hostname}",
            )
        )
        log_message(strip_rich_markup(message))
        remove_empty_lines(LOGFILE)
        print()
        print_times()
        print()
        print()
        continue
    except (EOFError, SSHException):
        # catch unexpected exceptions
        connection_fail_count += 1
        device_count -= 1
        skipped_devices.append(
            {"hostname": hostname, "ip": ipaddr, "reason": "SSHv1 only"}
        )
        print(
            f"Could not connect to {hostname} at {ipaddr}, remove it"
            " from the device inventory file"
        )
        log_message(strip_rich_markup(message))
        remove_empty_lines(LOGFILE)
        print()
        print_times()
        continue
    """
    Valid config file names are:
        hp_procurve-config-file.txt is used for all HP Procurve switches
        cisco_ios-config-file.txt is used for all Cisco IOS switches
        cisco_xe-config-file.txt is used for all Cisco IOS XE switches
        cisco_nxos-config-file.txt is used for all Cisco NXOS switches
        aruba_osswitch-config-file.txt is used for all Aruba OS switches
        aruba_cx-config-file.txt is used for all Aruba CX switches
    """
    cfg_file = f"{vendor}-config-file.txt"
    print()
    border = net_connect.find_prompt()
    print(f"Connected to: [cyan]{border}[/cyan]")
    print()
    border = "-" * (len(cfg_file) + len(hostname) + 18)
    print(f"[bold][blue]{border}[/blue][/bold]")
    print(
        f"Processing [bright_blue]'{cfg_file}'[/bright_blue] for [cyan]{hostname}[/cyan]"
    )
    border = "-" * (len(cfg_file) + len(hostname) + 18)
    print(f"[bold][blue]{border}[/blue][/bold]")
    remove_empty_lines(cfg_file)
    with open(cfg_file) as config_file:
        show_commands = config_file.readlines()
    ic(show_commands)
    # Netmiko normally allows 100 seconds for send_command to complete
    # delay_factor=2 would allow 200 seconds.
    output_show_str: str = ""
    time_out = args.timeout
    for command in show_commands:
        output_show = net_connect.send_command(
            command, strip_command=False, delay_factor=time_out
        )
        # ic(output_show)
        output_show_str = f"{output_show_str} \n\n !++++++++++++++ \n\n  {output_show}"

    # pull logs. Logs tend to time out because they are so large
    # you can set the timeout value up if they are timing out.
    if args.event != "":
        try:
            log_list = ["W", "I", "M", "D", "E", "1"]
            log_type = args.event.split(",")
            time_out = args.timeout
            for type in log_type:
                print(f"Processing show logging -{type} for {hostname}")
                output_event = f"output_event_{type}"
                if type not in log_list:
                    print(f"logging argument {type} for {hostname} is not supported")
                    continue
                if type == "1":
                    show_logging = "show logging"
                else:
                    show_logging = f"show logging -r -{type}"
                output_event = net_connect.send_command(
                    show_logging, strip_command=False, delay_factor=time_out
                )
                border = "-" * (len(cfg_file) + len(hostname) + 16)
                print(f"[bold][blue]{border}[/blue][/bold]")

                #  Write the show logging output to disk
                log_name = f"-log-{type}.txt"
                int_report = create_filename("CR-data", log_name)
                print(f"Writing show logging -{type} commands to {int_report}")
                with open(int_report, "w") as file:
                    file.write(output_event)
                border = "-" * (len(type) + len(int_report) + 36)
                print(f"[bold][blue]{border}[/blue][/bold]")
        except NetmikoTimeoutException:
            end_time = datetime.now()
            print(f"\nExec time: {end_time - now}\n")
            print(
                f"Time out processing -{type} logs for {hostname} at {ipaddr}. The connection timed out. Try setting -e to a higher value"
            )
            continue

    # Use textFSM to create a json object with interface stats
    print(
        f"collecting [bright_blue]'show interface'[/bright_blue] for [cyan]{hostname}[/cyan]"
    )

    output = net_connect.send_command("show interfaces", use_textfsm=True)
    border = "-" * (len(hostname) + 32)
    print(f"[bold][bright_blue]{border}[/bright_blue][/bold]")
    ic(output)
    # Use textFSM to create a json object with cdp neighbors
    print(
        f"collecting [bright_blue]'show cdp detail'[/bright_blue] for [cyan]{hostname}[/cyan]"
    )
    output_cdp = net_connect.send_command("show cdp neighbor detail", use_textfsm=True)
    border = "-" * (len(hostname) + 33)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # Use textFSM to create a json object with interface stats
    vendor = vendor.lower()
    match vendor:
        case "hp_procurve":
            template_path = os.getcwd()
            template_file = os.path.join(template_path, "sh_int_br.textfsm")
            print(
                f"collecting [bright_blue]'show interfaces brief'[/bright_blue] for [cyan]{hostname}[/cyan]"
            )
            output_show_int_br = net_connect.send_command(
                "show interfaces brief",
                strip_command=True,
                use_textfsm=True,
                textfsm_template=template_file,
            )
            # border = "-" * (len(cfg_file) + len(hostname) + 16)
            border = "-" * +(len(hostname) + 37)
            print(f"[bold][blue]{border}[/blue][/bold]")
            # Use textFSM to create a json object of show system
            print(
                f"collecting [bright_blue]'show system'[/bright_blue] for [cyan]{hostname}[/cyan]"
            )
            output_system = net_connect.send_command("show system", use_textfsm=True)
            border = "-" * +(len(hostname) + 29)
            print(f"[bold][blue]{border}[/blue][/bold]")
            #  Write the JSON system data to a file
            int_report = create_filename("Interface", "-system.txt")

            message = f"Writing the system json data for [blue]{hostname}[/blue] to \n[cyan]{int_report}[/cyan].\n"

            print_panel(
                message,
                title="System Data",
                subtitle=f"System data for {hostname} completed",
                border_style="cyan",
                title_emoji=emoji_for("saving"),
                expand=False,
            )

            # write the JSON system data to a file
            with open(int_report, "w") as file:
                output_system = json.dumps(output_system, indent=2)
                file.write(output_system)
            border = "-" * (len(int_report) + 1)
            print(f"[bold][blue]{border}[/blue][/bold]")
        case "cisco_ios":
            output_show_int_br = net_connect.send_command(
                "show interfaces status",
                strip_command=True,
                use_textfsm=True,
            )
        case "cisco_xe":
            output_show_int_br = net_connect.send_command(
                "show interfaces status",
                strip_command=True,
                use_textfsm=True,
            )

    # Use textFSM to create a json object with show lldp info remote
    print(
        f"collecting [bright_blue]'show lldp neighbors'[/bright_blue] for [cyan]{hostname}[/cyan]"
    )
    output_show_lldp = net_connect.send_command(show_lldp, use_textfsm=True)
    border = "-" * (len(hostname) + 37)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # collect arp
    print(
        f"collecting [bright_blue]'show arp'[/bright_blue] for [cyan]{hostname}[/cyan]"
    )
    output_text_arp = net_connect.send_command(show_arp, read_timeout=200)
    border = "-" * (len(hostname) + 26)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # Send show running
    print(
        f"Collecting [bright_blue]'show running-config'[/bright_blue] from [cyan]{hostname}[/cyan]"
    )
    # print(net_connect.find_prompt())
    output_text_run = net_connect.send_command(sh_run, read_timeout=360)
    border = "-" * (len(hostname) + 38)
    print(f"[bold][blue]{border}[/blue][/bold]")

    #  Write the JSON interface data to a file
    int_report = create_filename("Interface", "-interface.json")
    print(f"Writing [cyan]'interfaces json data'[/cyan] to\n {int_report}")
    with open(int_report, "w") as file:
        output = json.dumps(output, indent=2)
        file.write(output)
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # create a mac-address query file from the JSON interface data
    json_interface = create_filename("Interface", "-interface.json")
    output_mac_address = create_filename("port-maps", "-send-mac-addr.txt", "data")
    generate_mac_query_file_from_json(
        json_file_path=json_interface,
        output_file_path=output_mac_address,
        interface_key=interface_key,
        force_prefix=force_prefix,
    )

    border = "-" * (len(output_mac_address) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")

    remove_empty_lines(output_mac_address)
    with open(output_mac_address) as mac_add_file:
        show_commands = mac_add_file.readlines()
    ic(show_commands)
    # Netmiko normally allows 100 seconds for send_command to complete
    # delay_factor=2 would allow 200 seconds.
    output_mac_str = ""
    time_out = args.timeout
    for command in show_commands:
        output_show = net_connect.send_command(
            command, strip_command=False, delay_factor=time_out
        )
        # ic(output_show)
        output_mac_str = f"{output_mac_str} {output_show} \n"
        ic(output_mac_str)
        # output_mac_str = f"{output_show}"

    #  Write the show mac address commands output to disk
    int_report = create_filename("port-maps", "-mac-address.txt", "data")
    print(f"Writing '{maddr}' commands to\n {int_report}")
    with open(int_report, "w") as file:
        file.write(output_mac_str)
    # border = "-" * (len(dev_inv_file) + 25)
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # Disconnect from the switch and start writing data to disk
    net_connect.disconnect()

    #  Write the CR Data show commands output to disk
    int_report = create_filename("CR-data", "-CR-data.txt")
    print(f"Writing 'show commands' to\n {int_report}")
    with open(int_report, "w") as file:
        file.write(output_show_str)
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # Write the arp table plain text output to disk
    int_report = create_filename("port-maps", "-arp.txt", "data")
    print(f"Writing [bright_blue]'show arp'[/bright_blue] data to\n {int_report}")
    with open(int_report, "w") as file:
        file.write(output_text_arp)
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")

    #  Write the running config to disk
    int_report = create_filename("Running", "-running-config.txt")
    print(f"Writing 'show running' output to\n {int_report}")
    with open(int_report, "w") as file:
        file.write(output_text_run)
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # Write the JSON interface brief data to a file
    int_report = create_filename("Interface", "-int_br.txt")
    print(f"Writing 'show interfaces brief' data to\n {int_report}")
    with open(int_report, "w") as file:
        output_show_int_br = json.dumps(output_show_int_br, indent=2)
        file.write(output_show_int_br)
    # print("-" * (len(dev_inv_file) + 23))
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")
    # Write the JSON cdp neighbor data to a file
    int_report = create_filename("Interface", "-cdp.txt")
    print(f"Writing 'show cdp neighbor' data to\n {int_report}")
    with open(int_report, "w") as file:
        output_cdp = json.dumps(output_cdp, indent=2)
        file.write(output_cdp)
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")

    # Write the show lldp JSON data to a file
    int_report = create_filename("Interface", "-lldp.txt")
    print(f"Writing 'show lldp' data to\n {int_report}")
    with open(int_report, "w") as file:
        output_show_lldp = json.dumps(output_show_lldp, indent=2)
        file.write(output_show_lldp)
    border = "-" * (len(int_report) + 1)
    print(f"[bold][blue]{border}[/blue][/bold]")
    print()

    message = f"[bright_green]Successfully created config files for[/bright_green] [cyan]{hostname}[/cyan]"
    print(
        Panel.fit(
            message,
            title="✅ Done",
            border_style="cyan",
            # subtitle=f"Devices completed: {device_count}",
            subtitle=f"{device_count} device completed of {num_devices} total",
        )
    )
    print()
    print_times()
print()
stop = timeit.default_timer()
total_time = stop - start
# output running time in a nice format.
mins, secs = divmod(total_time, 60)
hours, mins = divmod(mins, 60)
# format timeouts, authentication failures, and connection fails
toc: str = ""
afc: str = ""
cfc: str = ""
svc: str = ""

if time_out_count == 1:
    toc = f"A total of [red]{time_out_count}[/red] device timed out.\n"
elif time_out_count == 0:
    toc = f"A total of [green]{time_out_count}[/green] device timed out.\n"
else:
    toc = f"A total of [red]{time_out_count}[/red] devices timed out.\n"

if auth_fail_count == 1:
    afc = (
        f"A total of [red]{auth_fail_count}[/red] device had authentication failures.\n"
    )
elif auth_fail_count == 0:
    afc = f"A total of [green]{auth_fail_count}[/green] devices had authentication failures.\n"
else:
    afc = f"A total of [red]{auth_fail_count}[/red] devices had authentication failures.\n"

if connection_fail_count == 1:
    cfc = f"A total of [red]{connection_fail_count}[/red] device  didn't send an SSH banner.\n"
elif connection_fail_count == 0:
    cfc = f"A total of [green]{connection_fail_count}[/green] devices didn't send an SSH banner.\n"
else:
    cfc = f"A total of [red]{connection_fail_count}[/red] devices didn't send an SSH banner.\n"

if sshv1_skip_count == 1:
    svc = f"A total of [red]{sshv1_skip_count}[/red] device was skipped due to unsupported SSHv1.\n"
elif sshv1_skip_count > 1:
    svc = f"A total of [red]{sshv1_skip_count}[/red] devices were skipped due to unsupported SSHv1.\n"
else:
    svc = ""

# ------
print(
    f"A total of {device_count} [cyan]device(s)[/cyan] out of {num_devices} in {dev_inv_file} were processed.\n"
    #    f"{toc}"
    f"{afc}"
    f"{cfc}"
    f"{svc}"
    f"\nData collection is complete.\n"
    f"Total running time: {hours} Hours {mins} Minutes {round(secs, 2)} Seconds\n"
)

current_path = os.getcwd()
sub_dir1: str = "Failure-Logs"
skipped_filename: str = "skipped_devices.csv"
skipped_devices_file: str = os.path.join(current_path, sub_dir1, skipped_filename)
write_skipped_devices_csv(skipped_devices_file)
print(f"[cyan]Skipped devices saved to {skipped_devices_file}[/cyan]")
print()
print_skipped_devices_table(skipped_devices)
