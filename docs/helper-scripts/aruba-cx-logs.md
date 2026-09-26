# Parsing Aruba CX logs

`CX-Log-Parse.py` takes a syslog export already saved to disk and turns it into a CSV. `CX-Log-Parse-API.py` does the same thing, but can also pull the log directly from a switch over the REST API instead of starting from a file. Both use the same regex to split each log line into: date, time, timezone, hostname, process, PID, event type, event ID, log level, module, interface, and message.

`python3 CX-Log-Parse.py -f logfile.txt`

Raw CX syslog lines pack the date, time, fractional seconds, and UTC offset into one unbroken token, e.g. `2024-05-15T21:46:01.398675-07:00`. There's no delimiter between the seconds and the timezone, so searching or sorting by date or time alone in a text editor means eyeballing a wall of similar-looking timestamps — you can't easily filter "just today" or "just this hour" without regex. Splitting Date, Time, and Timezone into their own CSV columns means a spreadsheet program (or a CSV tool like `csvlens`) can sort, filter, and search each of those fields independently, the same way it can for hostname, interface, or log level.

## Pulling logs directly from a switch

`CX-Log-Parse-API.py -i <ip>` logs into the switch's REST API to pull logs instead of reading a local file, which means it needs a password. The password is never accepted as a plaintext command-line argument — that would leave it sitting in plain view in shell history and process listings. Instead, use one of:

- `-p 1` — prompts for the password interactively (it isn't echoed to the terminal).
- The `cyberARK` environment variable — set it once per shell session with `export cyberARK=your_password`, and every run in that session picks it up automatically with no prompt.

If neither is set, the script prints a reminder of both options and exits instead of falling back to a default password.
