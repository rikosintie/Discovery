#!/usr/bin/env python3
"""
# ~/.config/sonicwall/tz370.env  (chmod 600)
SONICWALL_HOST=10.100.126.1
SONICWALL_USER=api_readonly
SONICWALL_PASS=your_password_here

Poll a SonicWall TZ370's SonicOS API for the ARP cache and write it to CSV.

Credentials are read from environment variables so nothing is hardcoded
in the script itself:

    SONICWALL_HOST   e.g. 10.100.126.1
    SONICWALL_USER   e.g. api_readonly
    SONICWALL_PASS   the account's password

Recommended usage:
    1. Create a file readable only by you, e.g. ~/.config/sonicwall/tz370.env:
           SONICWALL_HOST=10.100.126.1
           SONICWALL_USER=api_readonly
           SONICWALL_PASS=supersecret
       chmod 600 ~/.config/sonicwall/tz370.env

    2. Run with:
           set -a; source ~/.config/sonicwall/tz370.env; set +a
           python3 poll_arp_cache.py

    Or use python-dotenv (pip install python-dotenv) and uncomment the
    load_dotenv() call below to load that file automatically.

NOTE: The SonicOS API must be enabled first:
    Device | Settings | Administration | SonicOS API
    -> enable "RFC-2617 HTTP Basic Access authentication" (or another
       method — adjust the auth call below if you pick something else)

NOTE: This appliance almost certainly uses a self-signed cert, hence
verify=False below. For anything beyond a quick internal script, pull
down the appliance's cert and pin it instead of disabling verification.
"""

import csv
import os
import sys
from datetime import datetime, timezone

import requests
import urllib3

# from dotenv import load_dotenv
# load_dotenv(os.path.expanduser("~/.config/sonicwall/tz370.env"))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_credentials():
    host = os.environ.get("SONICWALL_HOST")
    user = os.environ.get("SONICWALL_USER")
    password = os.environ.get("SONICWALL_PASS")

    missing = [
        name
        for name, val in (
            ("SONICWALL_HOST", host),
            ("SONICWALL_USER", user),
            ("SONICWALL_PASS", password),
        )
        if not val
    ]
    if missing:
        sys.exit(f"Missing required environment variable(s): {', '.join(missing)}")

    return host, user, password


def main():
    host, user, password = get_credentials()
    base_url = f"https://{host}/api/sonicos"

    session = requests.Session()
    session.verify = False  # self-signed cert; see note above
    session.auth = (user, password)

    # Log in
    auth_resp = session.post(f"{base_url}/auth")
    auth_resp.raise_for_status()

    try:
        # NOTE: confirm the exact path against your firmware's API docs/browser
        # (Device | Settings | Administration | SonicOS API often has a link
        # to an interactive API explorer once enabled). "arp-cache" here is
        # a placeholder — adjust to whatever the real endpoint turns out to be.
        resp = session.get(
            f"{base_url}/arp-cache", headers={"Accept": "application/json"}
        )
        resp.raise_for_status()
        data = resp.json()
    finally:
        # Always log out to free the session, even if the GET failed
        session.delete(f"{base_url}/auth")

    entries = data.get("arp_cache", data)  # adjust based on actual response shape

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile = f"arp_cache_{timestamp}.csv"

    with open(outfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["IP Address", "Type", "MAC Address", "Interface", "Timeout"])
        for entry in entries:
            writer.writerow(
                [
                    entry.get("ip"),
                    entry.get("type"),
                    entry.get("mac"),
                    entry.get("interface"),
                    entry.get("timeout"),
                ]
            )

    print(f"Wrote {len(entries)} entries to {outfile}")


if __name__ == "__main__":
    main()
