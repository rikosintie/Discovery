def get_current_path(sub_dir1: str, extension: str = "", sub_dir2="") -> str:
    """
    returns a valid path regardless of the OS

    Args:
        sub_dir1 (str): name of the sub directory off the cwd required
        extension (str): string appended after hostname - ex. -interface.txt
        sub_dir2 (str, optional): if a nested sub_dir is used Defaults to "".

    Returns:
        str: full pathname of the file to be written
    """
    current_path = os.getcwd()
    extension = hostname + extension
    int_report = os.path.join(current_path, sub_dir1, sub_dir2, extension)
    return int_report


def remove_empty_lines(filename: str) -> str:
    """
    Removes empty lines from the file

    Args:
        filename (str): file in the cwd to be opened

    Returns:
        Nothing - updated file is written to disk
    """
    if not os.path.isfile(filename):
        print("{} does not exist ".format(filename))
        return
    with open(filename) as filehandle:
        lines = filehandle.readlines()

    with open(filename, "w") as filehandle:
        lines = filter(lambda x: x.strip(), lines)
        filehandle.writelines(lines)


def format_mac(mac: str) -> str:
    """
    Converts most common MAC address formats into all formats

    008041aefd7e - valid\n
    00-80-41-ae-fd-7e  - valid\n
    00:80:41:AE:FD:7E  - valid\n
    '0080.41ae.fd7e',  - valid\n
    00:80:41:ae:fd:7e  - valid\n
    '00:80:41:ae:fd:7e\n\t',  - valid

    Args:
        mac (str): A valid mac address format

    Returns:
        str: MAC_Types in aa:bb:cc:dd:ee:ff format
    """
    mac = re.sub("[.:-]", "", mac).lower()  # remove delimiters, convert to lc
    mac = "".join(mac.split())  # remove whitespaces
    assert len(mac) == 12  # length should be now exactly 12 (eg. 008041aefd7e)
    assert mac.isalnum()  # should only contain letters and numbers
    colon = mac
    hpe = mac
    cisco = mac
    ms = mac
    # convert mac in canonical form (eg. 00:80:41:ae:fd:7e)
    colon = ":".join(["%s" % (mac[i : i + 2]) for i in range(0, 12, 2)])
    # HPE format
    hpe = "-".join(["%s" % (mac[i : i + 6]) for i in range(0, 12, 6)])
    # Cisco format
    cisco = ".".join(["%s" % (mac[i : i + 4]) for i in range(0, 12, 4)])
    # MS format
    ms = "-".join(["%s" % (mac[i : i + 2]) for i in range(0, 12, 2)])
    # Build list of macs
    list1 = [colon, hpe, cisco, ms, mac]
    MAC_Types = "\n".join(list1)
    return MAC_Types
