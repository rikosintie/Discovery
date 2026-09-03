"""
Lists the files present in each of the discovery output directories and
saves those filename lists to CSV and Excel.

On a long discovery (multiple sites, or multiple wiring closets), the
customer will want a daily update on how many devices have been discovered
and had data pulled so far. Running this script drops a dated snapshot of
what's been collected in each output directory (CR-data, Interface,
port-maps/Final, Running) without having to open every folder by hand.

python filenames.py
"""

import csv
import os

import pandas as pd


def get_filenames(directory_path: str) -> list[str]:
    """
    Returns the sorted list of filenames in a directory.

    Args:
        directory_path (str): Directory to list.

    Returns:
        list[str]: Sorted filenames found in directory_path.
    """
    filenames = os.listdir(directory_path)
    filenames.sort()
    return filenames


def get_current_path() -> str:
    """
    Returns the current working directory.

    Returns:
        str: The current working directory.
    """
    return os.getcwd()


def save_to_excel(folder: str, filename: str, data: list[str]) -> None:
    """
    Saves a list of filenames to an Excel file.

    Args:
        folder (str): Sub directory off the cwd to write filename into.
        filename (str): Name of the Excel file to write.
        data (list[str]): Filenames to save, one per row.

    Returns:
        None — the Excel file is written to disk.
    """
    full_path = os.path.join(get_current_path(), folder, filename)
    df = pd.DataFrame(data, columns=["File Name"])
    df.to_excel(full_path, index=False)


def save_to_csv(folder: str, filename: str, data: list[str]) -> None:
    """
    Saves a list of filenames to a CSV file.

    Args:
        folder (str): Sub directory off the cwd to write filename into.
        filename (str): Name of the CSV file to write.
        data (list[str]): Filenames to save, one per row.

    Returns:
        None — the CSV file is written to disk.
    """
    full_path = os.path.join(get_current_path(), folder, filename)
    with open(full_path, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["File Name"])
        for row in data:
            csv_writer.writerow([row])


def main() -> None:
    """
    Lists the files in each discovery output directory and saves each
    directory's filename list to its own CSV and Excel file.
    """
    proj_directories = [
        "CR-data",
        "Interface",
        "port-maps/Final",
        "Running",
    ]

    for folder in proj_directories:
        directory_path = os.path.join(get_current_path(), folder)
        filenames = get_filenames(directory_path)

        # The port-maps folder stores its results in a subdirectory (Final).
        # This removes the "/" and -Final from the name.
        base_name = folder.split("/")[0] if "/" in folder else folder

        save_to_csv(folder, base_name + ".csv", filenames)
        save_to_excel(folder, base_name + ".xlsx", filenames)

    print("Filenames have been saved to CSV and Excel files.")


if __name__ == "__main__":
    main()
