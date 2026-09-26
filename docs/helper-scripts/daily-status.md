# Daily discovery status snapshot

On a long discovery — multiple sites, or multiple wiring closets — the customer will want a daily update on how many devices have been discovered and had data pulled so far. `filenames.py` lists the files present in each of the output directories (`CR-data`, `Interface`, `port-maps/Final`, `Running`) and saves each directory's filename list to its own CSV and Excel file, so a status snapshot can be shared without opening every folder by hand.

`python3 filenames.py`

The output files are named after the directory they came from (e.g. `Running/Running.csv`, `Running/Running.xlsx`), except for `port-maps/Final`, which is saved as `port-maps.csv`/`port-maps.xlsx`.
