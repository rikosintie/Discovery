[Home](https://github.com/rikosintie/Discovery/)<!-- omit from toc -->

# Getting Started<!-- omit from toc -->

- [1. Clone the Repository](#1-clone-the-repository)
- [2. Create a Virtual Environment](#2-create-a-virtual-environment)
- [3. Activate the Virtual Environment](#3-activate-the-virtual-environment)
- [4. Install Dependencies](#4-install-dependencies)
- [5. Deactivate the Virtual Environment](#5-deactivate-the-virtual-environment)

Follow these steps to set up and run the project:

## 1. Clone the Repository

```bash
git clone https://github.com/rikosintie/Discovery.git
cd Discovery
```

If you don't have git installed, you can download the zip file from the [repository](https://github.com/rikosintie/Discovery). Click on the green "Code" button and select "Download ZIP". Then unzip the file.

<p align="center" width="60%">
<img width="40%" src="https://github.com/rikosintie/Discovery/blob/main/images/GitHub-Code.png" alt="Github ZIP file">
</p>

NOTE: Once you have the repository cloned it is linked to the repository on github.com. You should issue a `git pull` once in a while to pull down any changes that have been made to the repository.

## 2. Create a Virtual Environment

`python -m venv venv --upgrade-deps --prompt="Discovery"`

This will create the standard "venv" directory but when activated will display "Discovery". I prefer this over using `python -m venv Discovery` because it's the standard way to create the virtual environment. But I like seeing Discovery instead of venv when I activate the environment.

The `--upgrade-deps` argument tells python to upgrade pip to the latest version when creating the virtual environment. You need internet access for pip to be upgraded. If you don't have internet access, remove the `--upgrade-deps` argument.

## 3. Activate the Virtual Environment

On Windows

`.\venv\Scripts\activate`

On macOS/Linux

`source venv/bin/activate`

Here is what my terminal looks like after activating:

<p align="center" width="100%">
<img width="100%" src="https://github.com/rikosintie/Discovery/blob/main/images/venv.png" alt="venv">
</p>

## 4. Install Dependencies

You can use `pip list` to list the packages currently installed. If you run it now you will see:

```bash
$ pip list
Package    Version
---------- -------
pip        23.3.2
setuptools 69.0.3
```

Now run the following:

`pip install -r requirements.txt`

You will see all the dependencies being downloaded and installed. Here is a snippet of the dependencies.

```bash
$ pip install -r requirements.txt
Collecting asttokens~=2.4.1 (from -r requirements.txt (line 1))
  Downloading asttokens-2.4.1-py2.py3-none-any.whl.metadata (5.2 kB)
Collecting bcrypt~=4.1.2 (from -r requirements.txt (line 2))
  Downloading bcrypt-4.1.2-cp39-abi3-manylinux_2_28_x86_64.whl.metadata (9.5 kB)
```

Now if we run `pip list` we will see that the dependencies have been installed:

```bash
$ pip list
Package       Version
------------- -------
asttokens     2.4.1
bcrypt        4.1.2
cffi          1.16.0
colorama      0.4.6
cryptography  41.0.7
executing     2.0.1
future        0.18.3
icecream      2.1.3
netmiko       4.3.0
ntc_templates 4.1.0
paramiko      3.4.0
pip           23.3.2
prettytable   3.9.0
pycparser     2.21
Pygments      2.17.2
PyNaCl        1.5.0
pyserial      3.5
PyYAML        6.0.1
scp           0.14.5
setuptools    69.0.3
six           1.16.0
textfsm       1.1.3
wcwidth       0.2.12

```

## 5. Deactivate the Virtual Environment

When you are finished, deactivate the environment

`deactivate`

You will need to activate the virtual environment each time you want to run the scripts.

----------------------------------------------------------------

[Home](https://github.com/rikosintie/Discovery/)<!-- omit from toc -->
[Usage](https://github.com/rikosintie/Discovery/blob/main/usage.md)<!-- omit from toc -->
[The Helper Scripts](https://github.com/rikosintie/Discovery/blob/main/Helper-scripts.md)<!-- omit from toc -->
