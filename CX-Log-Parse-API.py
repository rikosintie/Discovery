import argparse
import csv
import json
import os
import re

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

    # url = f"https://{ip}/rest/v1/logs/event"  # Example API endpoint
    url = f"https://{ip}/rest/v10.10/logs/event"
    # headers = {"Content-Type": "application/json"}

    try:
        # response = requests.get(url, headers=headers, data=creds, verify=False)
        response = session.get(url, verify=False)
        print(f"This is the response status code: {response.status_code}")
        # response.raise_for_status() # Uncomment this if you want to raise an exception for non-2xx status codes
        # test = response.text.splitlines()
        response_dict = json.loads(response.text)
        print(json.dumps(response_dict, indent=4))
        # print(f"Log: {test}")
        return response.text.splitlines()
        response.raise_for_status()
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
            parse_logs(log_lines, args.output)
            print(f"Logs fetched from switch {args.ip} and saved to {args.output}")
        else:
            print(f"Failed to fetch logs from {args.ip}")

    else:
        print("You must specify either a log file with -f or an IP address with -i.")
        parser.print_help()


if __name__ == "__main__":
    main()
