"""
usage
python CX-Log-Parse-API.py -f logfile.txt -o output.csv

Pull logs from a switch
python CX-Log-Parse-API.py -i 192.168.10.233 -u admin -p 1 -o 01_lab.csv

The password is never passed on the command line. Use -p 1 to be prompted for
it, or set the environment variable: export cyberARK=your_password

To view the reference documentation for the REST v10.xx API, access the following URL using a browser:
https://192.168.10.233/api/v10.10/
"""

import argparse
import csv
import getpass
import json
import os
import re
import sys
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# Regex pattern for log parsing, with flexible handling for interface field (which can be '-')
log_pattern = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2}\.\d+)(?P<timezone>[+-]\d{2}:\d{2}) (?P<hostname>\S+) (?P<process>\S+)\[(?P<pid>\d+)\]: (?P<event_type>\S+)\|(?P<event_id>\d+)\|(?P<log_level>\S+)\|(?P<module>\S+)\|(?P<interface>(?:\S+|-)?)\|(?P<message>.+)"
)


# Function to convert UNIX timestamp to Human readable
def convert_timestamp(microseconds: str) -> str:
    """
    Convert a UNIX timestamp in microseconds to a human-readable date and time.

    Args:
        microseconds (str): UNIX timestamp in microseconds from the CX switch.

    Returns:
        str: The date and time in a human-readable format (YYYY-MM-DD HH:MM:SS.ffffff).
    """
    HR_time: str = (
        datetime.fromtimestamp(float(microseconds) / 1e6)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S.%f")
    )
    return HR_time


# Function to parse log file
def parse_logs(log_lines: list[str], csv_filename: str) -> None:
    """
    Parses raw CX log lines with log_pattern and writes the matched fields
    to a CSV file.

    Args:
        log_lines (list[str]): Raw log lines, as read from a log file.
        csv_filename (str): Path to the CSV file to write.

    Returns:
        None — the CSV file is written to disk. Lines that don't match
        log_pattern are silently skipped.
    """
    with open(csv_filename, "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file)
        # Write CSV header
        csv_writer.writerow(
            [
                "Date",
                "Time",
                "Timezone",
                "Hostname",
                "Process",
                "PID",
                "Event Type",
                "Event ID",
                "Log Level",
                "Module",
                "Interface",
                "Message",
            ]
        )

        for line in log_lines:
            match = log_pattern.match(line)
            if match:
                csv_writer.writerow(match.groups())


# Function to retrieve logs from the Aruba CX switch via REST API
def fetch_logs_from_switch(
    ip: str, username: str, password: str, url: str
) -> list[str] | None:
    """
    Logs into an Aruba CX switch's REST API and fetches logs from the
    given URL.

    Args:
        ip (str): IP address of the switch.
        username (str): API username.
        password (str): API password.
        url (str): Full logs endpoint URL to fetch (see main() for how
            it's built from the -s/-u/--limit/etc. arguments).

    Returns:
        list[str] | None: The response body split into lines, or None if
        login or the log fetch failed.
    """
    creds: dict[str, str] = {"username": username, "password": password}
    session = requests.Session()
    try:
        login = session.post(
            # f"https://{ip}/rest/v10.10/login?since=yesterday", data=creds, verify=False
            f"https://{ip}/rest/v10.10/login",
            data=creds,
            verify=False,
        )
        print(f"This is the login code: {login.status_code}")
        firmware: requests.Response = session.get(
            f"https://{ip}/rest/v10.10/firmware", verify=False
        )
        print(firmware.json())
    except requests.exceptions.RequestException as e:
        print(f"Error logging into switch: {e}")
        sys.exit()

    # This URL contains API documentation from the switch
    # https://{ip address}/api/v10.10/#/Logs/get_logs_event
    # url = f"https://{ip}/rest/v10.10/logs/event?since=today"
    # url = f"https://{ip}/rest/v10.10/logs/event?since={since}" + args.since

    try:
        response = session.get(url, verify=False)
        print(f"This is the response status code: {response.status_code}")
        response.raise_for_status()  # Uncomment this if you want to raise an exception for non-2xx status codes
        response.close()
        return response.text.splitlines()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching logs from switch: {e}")
        return None


# Main function
def main() -> None:
    """
    Parses CLI arguments and either processes a local log file (-f) or
    fetches logs from an Aruba CX switch's REST API (-i), writing the
    result to a CSV file (-o) either way.
    """
    parser = argparse.ArgumentParser(
        description="Process logs from file or Aruba CX switch API."
    )
    parser.add_argument("-f", "--file", help="Log file to process")
    parser.add_argument(
        "-i", "--ip", help="IP address of the Aruba CX switch to pull logs from"
    )
    parser.add_argument(
        "-o", "--output", help="CSV output filename", default="log_output.csv"
    )
    parser.add_argument(
        "-n", "--username", help="Username for Aruba CX API", default="admin"
    )
    parser.add_argument(
        "-p",
        "--password",
        default="",
        help="use -p 1 to be prompted for password",
    )
    # - - - - - -
    parser.add_argument("-l", "--priority", help="Log Level to filter on", default="7")

    parser.add_argument(
        "-s", "--since", help="Return logs since", default="2025-01-02 17:00:29"
    )

    parser.add_argument("-u", "--until", help="Return logs until", default="")

    parser.add_argument("--limit", help="number of logs 1-1000", default="")

    parser.add_argument("-e", "--event_id_num", help="event id", default="")

    parser.add_argument(
        "-c", "--EVENT_CATEGORY", help="Log_Info, Log_Warn, etc.", default=""
    )
    # - - - - - -
    args = parser.parse_args()
    priority: str = args.priority
    since: str = args.since
    until: str = args.until
    limit: str = args.limit
    event_id_num: str = args.event_id_num  # optional parameter for event ID filtering
    event_cat: str = args.EVENT_CATEGORY
    ip: str = args.ip
    url: str = f"https://{ip}/rest/v10.10/logs/event?priority={priority}&since={since}&until={until}&limit={limit}&ID={event_id_num}&EVENT_CATEGORY={event_cat}"
    # url: str = f"https://{ip}/rest/v10.10/logs/event"
    # print(f"since: {since}, limit: {limit}")
    print(f"URL: {url}")

    log_lines: list[str] | None
    if args.file and os.path.isfile(args.file):
        # Read logs from file
        with open(args.file, "r") as log_file:
            log_lines = log_file.readlines()
        parse_logs(log_lines, args.output)
        print(f"Logs processed and saved to {args.output}")

    elif args.ip:
        # Check for the password, exit if it doesn't exist
        password: str | None = ""
        if args.password != "":
            password = getpass.getpass(prompt="Input the Password:")
        elif os.environ.get("cyberARK"):
            password = os.environ.get("cyberARK")
        else:
            print(
                "\nNo password was found. Use:\n\n"
                "python CX-Log-Parse-API.py -i <ip> -p 1\n\n"
                "on the terminal to be prompted for a password,\n"
                "or set the environment variable:\n\n"
                "export cyberARK=your_password\n\n"
                "on the terminal\n"
            )
            sys.exit()

        # Fetch logs from Aruba CX switch
        log_lines = fetch_logs_from_switch(args.ip, args.username, password, url)
        if log_lines:
            # Convert log lines to JSON
            response_dict = json.loads("\n".join(log_lines))

            # Print the entire JSON structure to see available keys
            # print(json.dumps(response_dict, indent=4))  # Add this to inspect the JSON

            # Define the headers
            headers = [
                "Date",
                "Time",
                "Hostname",
                "Priority",
                "Event_ID",
                "LOG_TYPE",
                "MGMT_Role",
                "Message",
            ]

            # Open CSV file for writing
            with open(args.output, "w", newline="") as csvfile:
                csvwriter = csv.writer(csvfile)
                # Write the headers
                csvwriter.writerow(headers)

                # Iterate over each entity
                for entity in response_dict["entities"]:
                    hostname = entity.get("_HOSTNAME", "")
                    priority = entity.get("PRIORITY", "")
                    timestamp = entity.get("__REALTIME_TIMESTAMP", "")
                    mgmt_role = entity.get("MGMT_ROLE", "")
                    event = entity.get("OPS_EVENT_ID", "")

                    # convert UNIX time to human readable and parse
                    HR_timestamp = convert_timestamp(timestamp)
                    parts: list[str] = HR_timestamp.split(" ")
                    date: str = parts[0]
                    time: str = parts[1]

                    # Parse the message
                    message = entity.get("MESSAGE", "")
                    if message:
                        parts = message.split("|")
                        if len(parts) >= 3:
                            event = parts[1]
                            log_type = parts[2]
                        else:
                            event, log_type = "", ""
                        message = message.split("|")[-1]
                    else:
                        event, log_type = "", ""

                    # Write the row to the CSV file
                    csvwriter.writerow(
                        [
                            date,
                            time,
                            hostname,
                            priority,
                            event,
                            log_type,
                            mgmt_role,
                            message,
                        ]
                    )
                print(f"Logs fetched from switch {args.ip} and saved to {args.output}")
        else:
            print(f"Failed to fetch logs from {args.ip}")

    else:
        print(f"Failed to fetch logs from {args.ip}")


if __name__ == "__main__":
    main()
