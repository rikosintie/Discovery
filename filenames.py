import csv
import os

import pandas as pd

# set directory_path to the directory you want to read.
# reads all the files in the directory and saves the names to excel, csv.


def get_filenames(directory_path):
    # Get a list of all filenames in the directory
    filenames = os.listdir(directory_path)
    return filenames


def save_to_csv(filename, data):
    loc = get_current_path()
    # loc = loc + '\\running\\'
    filename = loc + "/" + filename
    with open(filename, "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["File Name"])
        for row in data:
            csv_writer.writerow([row])


def save_to_excel(filename, data):
    df = pd.DataFrame(data, columns=["File Name"])
    df.to_excel(filename, index=False)


def get_current_path():
    current_path = os.getcwd()
    return current_path


if __name__ == "__main__":
    directory_path = "/home/mhubbard/Insync/michael.hubbard999@gmail.com/GoogleDrive/04_Tools/Discovery/Running/"  # Replace this with the actual directory path
    # directory_path = get_current_path()

    # Get the filenames from the directory
    filenames = get_filenames(directory_path)

    # Save to CSV
    csv_filename = "filenames.csv"
    save_to_csv(csv_filename, filenames)

    # Save to Excel
    excel_filename = "filenames.xlsx"
    save_to_excel(excel_filename, filenames)

    print("Filenames have been saved to CSV and Excel files.")
