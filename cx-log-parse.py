r"""
Parses an Aruba CX syslog export into a CSV.

Reads a log file already saved to disk (one CX syslog line per row, e.g.
exported via CX-Log-Parse-API.py or copy/pasted from a terminal session) and
writes each line's date, time, timezone, hostname, process, PID, event type,
event ID, log level, module, interface, and message to a CSV file with the
same basename.

The CSV can be imported into a spreadsheet program such as Excel, LibreOffice Calc or Google Sheets for easy
sorting and searching.

python CX-Log-Parse.py -f <log filename>
"""

import argparse
import csv
import re
import sys
from pathlib import Path

__author__ = "Michael Hubbard"
__author_email__ = "michael.hubbard999@gmail.com"
__author_email__ = "mhubbard@network-dev.com"
__copyright__ = ""
__license__ = "Unlicense"
# -*- coding: utf-8 -*-
# cx-Log-parse.py

# Updated regex pattern to account for either a value like "1/1" or "-"
log_pattern = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2}\.\d+)(?P<timezone>[+-]\d{2}:\d{2}) (?P<hostname>\S+) (?P<process>\S+)\[(?P<pid>\d+)\]: (?P<event_type>\S+)\|(?P<event_id>\d+)\|(?P<log_level>\S+)\|(?P<module>\S+)\|(?P<interface>(?:\S+|-)?)\|(?P<message>.+)"
)

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--Log_filename", dest="Log_filename")
args = parser.parse_args()
Log_filename: str = args.Log_filename


if Log_filename is None:
    print("-f Log filename is a required argument")
    sys.exit()

csv_filename: str = Path(Log_filename).stem + ".csv"

# Get path and add Log Filename to it
my_dir: Path = Path.cwd()

Log_file_Exists: Path = my_dir.joinpath(Log_filename)

# Open log file and CSV file
if Log_file_Exists.exists():
    with (
        open(Log_filename, "r") as log_file,
        open(csv_filename, "w", newline="") as csv_file,
    ):
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

        # Parse each log line
        for line in log_file:
            match = log_pattern.match(line)
            if match:
                # Write the captured groups to the CSV
                csv_writer.writerow(match.groups())
    print(f"Log file saved to: {csv_filename}")
else:
    print(f"Log file {Log_filename} does not exist")
    sys.exit()
