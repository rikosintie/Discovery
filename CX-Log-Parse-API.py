import argparse
import csv
import json
import os
import re
from datetime import datetime

import requests

"""
usage
python CX-Log-Parse-API.py -f logfile.txt -o output.csv
python CX-Log-Parse-API.py -i 192.168.10.233 -u vector -p H3lpd3sk -o 01_lab.csv
To view the reference documentation for the REST v10.xx API, access the following URL using a browser:
https://192.168.10.233/api/v10.10/
"""

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
    HR_time: str = datetime.fromtimestamp(float(microseconds) / 1e6).strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )
    return HR_time


# Function to parse log file
def parse_logs(log_lines, csv_filename):
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
def fetch_logs_from_switch(ip, username, password):
    creds: dict[str] = {"username": username, "password": password}
    session = requests.Session()
    try:
        login = session.post(
            f"https://{ip}/rest/v10.10/login", data=creds, verify=False
        )
        print(f"This is the login code: {login.status_code}")
        firmware: list[str] = session.get(
            f"https://{ip}/rest/v10.10/firmware", verify=False
        )
        print(firmware.json())
    except Exception as e:
        print(f"Error logging into switch: {e}")

    # This URL contains API documentation
    # https://{ip address}/api/v10.10/#/Logs/get_logs_event
    url = f"https://{ip}/rest/v10.10/logs/event"

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
def main():
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
        "-u", "--username", help="Username for Aruba CX API", default="admin"
    )
    parser.add_argument(
        "-p", "--password", help="Password for Aruba CX API", default="admin"
    )

    args = parser.parse_args()

    if args.file and os.path.isfile(args.file):
        # Read logs from file
        with open(args.file, "r") as log_file:
            log_lines = log_file.readlines()
        parse_logs(log_lines, args.output)
        print(f"Logs processed and saved to {args.output}")

    elif args.ip:
        # Fetch logs from Aruba CX switch
        log_lines = fetch_logs_from_switch(args.ip, args.username, args.password)
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
                    parts: str = HR_timestamp.split(" ")
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
