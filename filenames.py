import csv
import os
from pathlib import Path

import pandas as pd

# reads all the files in the collection directories and saves the names to
# an excel, and csv file.


def get_filenames(directory_path):
    # Get a list of all filenames in the directory
    filenames = os.listdir(directory_path)
    filenames = sorted(filenames)
    return filenames


# def save_to_excel(filename, data):
#     df = pd.DataFrame(data, columns=["File Name"])
#     df.to_excel(filename, index=False)


def get_current_path():
    current_path = os.getcwd()
    # current_path = os.path.join(current_path, "Running")

    return current_path


def save_to_excel(folder, filename, data):
    loc = get_current_path()
    filename: str = os.path.join(loc, folder, filename)
    df = pd.DataFrame(data, columns=["File Name"])
    df.to_excel(filename, index=False)


def save_to_csv(folder, filename, data):
    loc = get_current_path()
    filename: str = os.path.join(loc, folder, filename)

    with open(filename, "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["File Name"])
        for row in data:
            csv_writer.writerow([row])


def main():
    proj_directories = [
        "CR-data",
        "Interface",
        "port-maps/Final",
        "Running",
    ]

    for folder in proj_directories:
        # directory_path = "/home/mhubbard/Insync/michael.hubbard999@gmail.com/GoogleDrive/04_Tools/Discovery/Running/"  # Replace this with the actual directory path
        directory_path = get_current_path()
        directory_path = os.path.join(directory_path, folder)
        # Get the filenames from the directorycurrent_path = os.path.join(current_path, "Running")
        filenames = get_filenames(directory_path)

        # Save to CSV
        # The port-maps folder stores the results in a subdirectory Final.
        # This removes the "/" and -Final from the name.
        if "/" in folder:
            csv_filename = folder.split("/")[0] + ".csv"
        else:
            csv_filename = folder + ".csv"

        save_to_csv(folder, csv_filename, filenames)

        # Save to Excel
        # This removes the "/" and -Final from the name.
        if "/" in folder:
            excel_filename = folder.split("/")[0] + ".xlsx"
        else:
            excel_filename = folder + ".xlsx"
        save_to_excel(folder, excel_filename, filenames)

    print("Filenames have been saved to CSV and Excel files.")


if __name__ == "__main__":
    main()
