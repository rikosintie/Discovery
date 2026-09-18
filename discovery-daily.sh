#!/bin/bash
set -e

source ~/.config/discovery/cyberark.env

cd ~/Documents/04_tools/Discovery

source venv/bin/activate
python3 snmp_arp_cache.py
python3 config-pull.py -s jc-4500
python3 config-pull.py -s jcedge
python3 arp.py -s jcedge -c jc-core
python3 merge-firewall-arp.py -c jc-core
python3 port-map.py -s jcedge -c jc-core -d 10.100.126.6

deactivate

git add .
git diff --cached --quiet || git commit -m "Daily discovery run $(date '+%Y-%m-%d %H:%M')"

echo "$(date '+%Y-%m-%d %H:%M') - run completed, exit $?" >> ~/discovery-last-run.txt
