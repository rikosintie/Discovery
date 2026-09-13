## Appendix: grep, awk, sort, and cut — Five Worked Examples

### Why

Most network engineers coming from Windows have never used the core POSIX
text tools. This appendix walks through five real examples of using `grep`
(and its usual pipeline partners `awk`, `sort`, and `cut`) to rapidly pull
data out of switch configs, nmap scans, syslogs, and systemd unit files —
the kind of thing you'd otherwise be doing by hand in a text editor.

If you're on Windows, see [Install Coreutils for Windows](Getting_Started.md#install-coreutils-for-windows)
to get native versions of these tools, and the
[grep pipeline examples](usage.md#find-connected-ports) in the Usage guide
for PowerShell equivalents.

### grep

One of the best tools in Linux! You can search a directory, or recursively
through the file system, for a pattern inside a file.

From the man page:

```text
NAME
       grep - print lines matching a pattern

SYNOPSIS
       grep [OPTIONS] PATTERN [FILE...]
       grep [OPTIONS] -e PATTERN ... [FILE...]
       grep [OPTIONS] -f FILE ... [FILE...]

DESCRIPTION
       grep searches for PATTERN in each FILE. A FILE of "-" stands for
       standard input. If no FILE is given, recursive searches examine the
       working directory, and nonrecursive searches read standard input. By
       default, grep prints the matching lines.
```

### Example 1 — Pulling management IPs out of a directory of configs

I have backups of several switches in a directory. I wanted to pull out the
management IP address for each switch. I knew they all started with
`10.56.246.` and had a `255.255.255.0` mask.

I used a regular expression (regex) to look for `10.56.246.` followed by any
number from 0-9. I then passed the results of that to `grep` again, using the
`|` operator, to strip off the `ip address`, `ntp server`, etc. lines that
also happened to match.

Regular expressions are beyond the scope of this book, but they're very
powerful for searching. A Google search for regex will return many articles
on how to use them. I like this one:
[Computer Hope Regex Examples](https://www.computerhope.com/unix/ugrep.htm).

!!! Tip "Regex in a GUI text editor, too"
    In the gedit text editor built into Ubuntu you can use regex expressions
    for search/replace. I had a batch of files whose real site names were
    four characters long, and I wanted to change the real name to `site`. I
    just hit Ctrl+H, selected regex, and entered `^....` in the find box and
    `site` in the replace box. The `^` means "start of line," and each `.`
    means "match one character."

```text
mhubbard@1S1K-G5-5587:~/Dropbox/01_test/configs/DataCenter$ grep -r 10.56.246.[0-9]

site1-6880x.wri: ip address 10.56.246.178 255.255.255.0
site1-6880x.wri: network 10.56.246.178 0.0.0.0
site1-6880x.wri:ntp server 10.56.246.56 prefer
site2-6880x.wri: ip address 10.56.246.58 255.255.255.0
site2-6880x.wri: network 10.56.246.58 0.0.0.0
site2-6880x.wri:ntp server 10.56.246.56 prefer
site3-6880x.wri: ip address 10.56.246.229 255.255.255.0
site3-6880x.wri: network 10.56.246.229 0.0.0.0
```

Now with a second `grep` chained on, to keep only the lines that also have
the subnet mask on them:

```text
mhubbard@1S1K-G5-5587:~/Dropbox/test/configs/DataCenter$ grep -r 10.56.246.[0-9] | grep 255.255.255.0

site1-6880x.wri: ip address 10.56.246.178 255.255.255.0
site2-6880x.wri: ip address 10.56.246.58 255.255.255.0
site3-6880x.wri: ip address 10.56.246.229 255.255.255.0
site4-6880xx.wri: ip address 10.56.246.214 255.255.255.0
site5-6880x.wri: ip address 10.56.246.221 255.255.255.0
site6-6880x.wri: ip address 10.56.246.241 255.255.255.0
site7-6880x.wri: ip address 10.56.246.219 255.255.255.0
site8-6880X.wri: ip address 10.56.246.133 255.255.255.0
site9-6880x.wri: ip address 10.56.246.51 255.255.255.0
site10-6880x.wri: ip address 10.56.246.180 255.255.255.0
site11-6880x.wri: ip address 10.56.246.194 255.255.255.0
```

If I just want the IP address, I can add `awk` to print only the 4th field
on the line:

```bash
grep -r 10.56.246.[0-9] | grep 255.255.255.0 | awk '{ print $4 }'
```

```text
10.56.246.178
10.56.246.58
10.56.246.229
10.56.246.214
10.56.246.221
10.56.246.241
10.56.246.219
10.56.246.133
```

If you have IP addresses spread across multiple VLANs/subnets, use `grep -E`
with the regex `[0-9]{1,3}\.` instead of hardcoding the octets. That uses a
"quantifier" to find a digit 1, 2, or 3 times, followed by a literal `.` —
the `\` tells grep the `.` isn't a regex wildcard but a real dot. That's
called "escaping." The `-E` flag is required and is called extended regex.

### Example 2 — Finding a handful of Dell switches on a busy subnet

A while back I needed to find a handful of Dell switches on a large subnet
full of Dell computers and other devices. Since almost all of the MAC
addresses were Dell, just looking for MAC addresses didn't help.

I ran nmap and saved the output to a file:

```bash
sudo nmap -sS -T4 -sC -p23 -oA powerconnect -n -Pn --open --stylesheet nmap-bootstrap.xsl 10.112.69.1-50
```

Looking at the file, it was obvious that the switches returned
`Ports: 23/open/tcp//telnet///`. Contents of a snippet from
`powerconnect.gnmap`:

```text
# Ports scanned: TCP(1;23) UDP(0;) SCTP(0;) PROTOCOLS(0;)
Host: 10.112.69.2 () Status: Up
Host: 10.112.69.2 () Ports: 23/open/tcp//telnet///
Host: 10.112.69.3 () Status: Up
Host: 10.112.69.3 () Ports: 23/open/tcp//telnet///
Host: 10.112.69.4 () Status: Up
Host: 10.112.69.4 () Ports: 23/open/tcp//telnet///
```

A quick `grep` returned just the IP addresses of the switches. The `awk`
command after the pipe just means "print the second field in the stream" —
in this example `Host:` is the first field.

```bash
grep telnet/// powerconnect.gnmap | awk '{ print $2 }'
```

```text
10.112.69.2
10.112.69.3
10.112.69.4
10.112.69.5
10.112.69.6
10.112.69.7
10.112.69.8
10.112.69.9
10.112.69.10
10.112.69.11
10.112.69.14
10.112.69.15
10.112.69.16
10.112.69.17
10.112.69.18
10.112.69.19
10.112.69.21
10.112.69.22
10.112.69.23
10.112.69.44
```

### Example 3 — Finding unique IPs in a massive syslog

In this example, I was looking for a set of switches that had IP addresses
in the `10.255.255.` range. The syslog was massive, so opening it in an
editor and using its search feature was impractical. But piping the
`grep`/`awk` combo to the `sort` command returned only unique IP addresses
almost immediately.

```bash
grep 10.255.255 SyslogCatchAll.txt.001 | awk '{ print $4 }' | sort -u
```

```text
10.255.255.110
10.255.255.111
10.255.255.113
10.255.255.13
10.255.255.14
10.255.255.17
```

### Example 4 — Pulling ports by manufacturer across a whole directory

I had a directory with 8 files in it. They contained VLAN IDs, IP addresses,
MAC addresses, port numbers, and manufacturer names. I needed to pull out
just the ports with certain manufacturer names. A little `grep`, with some
`sort` thrown in, and the job is done!

Here's a listing of the files in the directory (some information removed for
clarity):

```text
RPU-Springs-ports.txt
RPUVidSec-ports.txt
UOC-BldgB-Water-ports
UOC1stSW1-ports.txt
UOC1stSW2-ports.txt
UOCCore-ports.txt
UOCbldgB-Sw1-ports.txt
UOCbldgB-Sw2-ports.txt
```

Here's the `grep` command:

```bash
grep -E 'Uni|Axi|Aru|Chec|Sam|Sony|Hew|Honey|SHA|Pronet|IB|Digibo|Siemens|Tanta|Bosch|Videx|Industr' *.txt | sort -u -b -k 1 -k 6 -k 5
```

The options:

- `-E` — interpret PATTERN as an extended regular expression. Without this
  I'd have to use `\|` instead of just `|` to get the OR function.
- `Uni|Axi|...` — the manufacturer name fragments I wanted to find.
- `*.txt` — search all files with a `.txt` extension.
- `sort` — pipe the output of `grep` to the `sort` command.
- `-u` — unique.
- `-b` — ignore leading blanks.
- `-k` — sort a table on any column number using the `-k` option.

The result (truncated for space — there were a lot more ports returned):

```text
RPU-Springs-ports.txt: 905 10.80.152.168 9c1c.12c4.f84a Gi0/9 ArubaaHe
RPU-Springs-ports.txt: 905 10.80.153.196 3c52.82bd.14b1 Gi0/2 HewlettP
UOC-BldgB-Water-ports: 64 10.14.64.4 000b.d801.8b94 Gi1/0/20 Industri
UOC-BldgB-Water-ports: 905 10.80.152.63 9c1c.12c4.f846 Gi1/0/24 ArubaaHe
UOC-BldgB-Water-ports: 905 10.80.152.69 0009.9f00.17c4 Gi1/0/13 Videx
UOC-BldgB-Water-ports: 905 10.80.152.80 e4e7.49a3.dde5 Gi1/0/24 HewlettP
UOC1stSW1-ports.txt: 63 10.14.63.212 0004.6368.d0e9 Gi0/44 BoschSec
UOC1stSW1-ports.txt: 65 10.14.65.154 0025.5a22.31e3 Gi0/40 Tantalus
UOC1stSW1-ports.txt: 905 10.195.1.190 fc15.b475.1b69 Gi0/37 HewlettP
UOC1stSW1-ports.txt: 905 10.80.152.189 f09f.fc30.119a Gi0/39 SHARP
UOC1stSW1-ports.txt: 905 10.80.152.61 0003.2d2a.764c Gi0/28 IBASETec
UOC1stSW2-ports.txt: 905 10.80.152.216 00a0.0306.d1fa Gi0/41 SiemensS
UOCCore-ports.txt: 101 10.253.196.2 001c.7f81.2483 Gi2/23 CheckPoi
UOCCore-ports.txt: 260 10.251.80.10 001c.7f81.2480 Gi2/24 CheckPoi
UOCCore-ports.txt: 905 10.80.152.23 0009.9fff.0aa6 Gi4/10 Videx
UOCbldgB-Sw1-ports.txt: 905 10.80.152.44 0009.9f00.21bf Gi1/0/16 Videx
UOCbldgB-Sw2-ports.txt: 905 10.80.152.63 9c1c.12c4.f846 Gi1/0/13 ArubaaHe
```

These 8 switches had almost 400 ports (48 &times; 8), and this took less
than a second to do. Manually, I would have had to open each of the 8 files,
look for the manufacturer, and then copy the information to a new file. I
was migrating 72 sites and had to do this for each site — some sites had as
many as 22 IDFs!

### Example 5 — Pulling IP/port/name out of a set of systemd unit files

Here's a listing of the files in `/etc/systemd/system/`:

```text
-rw-r--r-- 1 root root 1155 Aug  2 13:14 haas-firewall.service
-rw-r--r-- 1 root root  730 Aug  2 13:14 haas-firewall.timer
-rw-r--r-- 1 root root  327 Aug  2 18:13 haas-minimill.service
```

Each file has the same format, with a different IP, port, and name:

```ini
[Unit]
Description=Logger for ST30
After=network.target

[Service]
User=haas
WorkingDirectory=/home/haas/Haas_Data_collect/machines/st30
ExecStart=/usr/bin/python3 /home/haas/Haas_Data_collect/haas_logger2.py -a -t 192.168.10.143 --port 5053 --name st30
Type=idle

[Install]
WantedBy=multi-user.target
```

I wanted a list of just the IP, port, and name. `grep -Ei "python3"` finds
the `ExecStart=` line in each file (case-insensitively), and `cut -d' '
-f4-` drops the first three space-separated fields (`ExecStart=/usr/bin/python3`
and the script path), keeping everything from the `-a` flag onward:

```bash
grep -Ei "python3" /etc/systemd/system/haas*.service | cut -d' ' -f4-
```

```text
-t 192.168.10.143  --port 5055 --name MINIMILL
-t 192.168.10.143 --port 5060 --name ST10Y
-t 192.168.10.143 --port 5053 --name st30
-t 192.168.10.143 --port 5052 --name st30l
-t 192.168.10.143 --port 5054 --name st40
-t 192.168.10.143 --port 5056 --name ST41
-t 192.168.10.143 --port 5056 --name ST42
-t 192.168.10.143 --port 5057 --name ST43
-t 192.168.10.143 --port 5068 --name ST44
-t 192.168.10.143 --port 5057 --name TEST1
-t 192.168.10.143 --port 5051 --name TEST2
-t 192.168.10.143 --port 5051 --name VF2SS
-t 192.168.10.143 --port 5059 --name VF5SS
```

I hope that these examples have shown you how useful the `grep` command is!
