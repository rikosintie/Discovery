# Using PowerShell

----------------------------------------------------------------

![screenshot](img/PowerShell2.resized.jpeg)

----------------------------------------------------------------

Here are the steps I took to get Windows terminal installed and the latest version of PowerShell configured with history and some other Linux like features.

## Getting Started

The first step is installing the Windows Terminal. While not strictly required, you could use the cmd.exe shell, I find the Windows Terminal a much better solution. It allows:

Multiple applications in one application

- PowerShell
- WSL
- Git Bash
- CMD.exe
- Azure Cloud Shell

Here is a screenshot of my terminal:

----------------------------------------------------------------
![screenshot](img/terminal.png)

----------------------------------------------------------------

You can see that I have organized it so that Ubuntu 24.04 is at the top, then PowerShell 7, then Git Bash, then Command Prompt. The PowerShell without a number is the builtin version 5.1. Since I use WSL and PowerShell 7.5 the most, this makes sense for me. After we install PowerShell 7.5, I'll show you how to modify the order.

This article: [Windows Terminal vs. Command Prompt vs. PowerShell: Which Should You Use?](https://www.howtogeek.com/windows-terminal-vs-command-prompt-vs-powershell-what-to-use-when/) covers the differences between cmd.exe, powershell, wsl, and Windows Terminal. To sum up:

----------------------------------------------------------------

***Windows Terminal is the newest member of the group. Rather than being a shell itself, it serves as a modern interface for hosting multiple shells. You can run CMD, PowerShell, and even Linux distributions through Windows Subsystem for Linux (WSL) all within a single, customizable window. With features like tabs, Unicode support, and GPU-accelerated rendering, it makes multitasking smoother and more efficient.***

----------------------------------------------------------------

### Install Windows Terminal

Installing the Windows Terminal is simple.

- click the start menu
- Type `microsoft store` and press `enter`
- search for `Windows Terminal`
- Click on the `Free` button
- click on `Get`

----------------------------------------------------------------

![screenshot](img/wterminal.PNG)

----------------------------------------------------------------

### Install the latest version of PowerShell core

Windows 11 ships with PowerShell 5.1 installed. I don't understand all the reasons behind it, but PowerShell 7.5 is the latest version and it installs *BESIDE* PowerShell 5.1. That is really confusing and both versions store there `$PROFILE` in separate locations!

Open cmd.exe and paste the following code:

`winget install --id Microsoft.PowerShell --source winget`

This will install the latest version of PowerShell 7. If PowerShell 7 is already installed, it will fail and tell you to run upgrade instead.

In that case, run the following code to verify that PowerShell is up to date:

`winget upgrade --id Microsoft.PowerShell --source winget`

#### Check the Powershell version

Search `PowerShell` in Windows search bar and open it. Once you are in the PowerShell terminal you can check the version with `$PSVersionTable`. Here is what the output looked like on my fresh install:

```text
(Discovery) PS C:\Users\mhubbard.PU\Documents\04_tools\Discovery> $PSVersionTable

Name                           Value
----                           -----
PSVersion                      7.5.1
PSEdition                      Core
GitCommitId                    7.5.1
OS                             Microsoft Windows 10.0.26100
Platform                       Win32NT
PSCompatibleVersions           {1.0, 2.0, 3.0, 4.0…}
PSRemotingProtocolVersion      2.3
SerializationVersion           1.1.0.1
WSManStackVersion              3.0
```

### Add a persistent history and command search

This is a must have feature and gives PowerShell some [zsh](https://github.com/ohmyzsh) like capabilities. First we will open the PowerShell configuration file.

#### Create the PowerShell 7 profile

For some reason installing PowerShell 7 with winget didn't create the profile. We will use this PowerShell code to do it:

```bash
if (!(Test-Path -Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force
}
```

You can see the path to the file by running:

```PowerShell hl_lines='1'
 echo $profile
C:\Users\mhubbard.PU\Documents\PowerShell\Microsoft.PowerShell_profile.ps1
```

We want to modify the profile. Open it using `notepad $PROFILE`. Then paste in the following:

```powershell linenums="1" hl_lines="1-5 7 12 15"
Import-Module PSReadLine
Set-PSReadLineOption -PredictionSource History
Set-PSReadLineOption -HistorySearchCursorMovesToEnd # Optional: moves cursor to end of matched command
Set-PSReadLineKeyHandler -Key UpArrow -Function HistorySearchBackward
Set-PSReadLineKeyHandler -Key DownArrow -Function HistorySearchForward

function Invoke-CsvLensWithArgs {
    csvlens.exe --color-columns --no-headers @args
}

# --- Custom aliases for Discovery tool ---
Set-Alias -Name cl -Value Invoke-CsvLensWithArgs
# --- End custom aliases for Discovery tool ---

 Invoke-Expression (& { (zoxide init powershell | Out-String) })
```

The first line imports the `PSReadLine` module. This tells PowerShell to read the history file. I did a bunch of Gemini searching and PowerShell still isn't displaying history from the previous session. In other words, when I close PowerShell I lose the history.

The next 4 lines setup a history search capability. That is so useful, if you have typed a command previously, you just type the first few letters and tap the up arrow. It will cycle through all commands that match.

The `function Invoke-CsvLensWithArgs` creates an alias for csvlens that automatically adds the `--color-columns` and `--no-headers` needed to view the device inventory files.

!!! note
    On Mac/Linux, use `csvlens --color-columns --no-headers @args` instead of `csvlens.exe --color-columns --no-headers @args`

The line `Set-Alias -Name cl -Value Invoke-CsvLensWithArgs`, builds the alias. In this case, typing `cl` invokes the alias.

Finally, the line `Invoke-Expression (& { (zoxide init powershell | Out-String) })` adds `zoxide` to the profile. Zoxide is a tool that builds a database of the directories you go to then allows you to `jump` to them with just a few keystrokes.

For example, once you have installed the scripts to the `Discovery` folder and navigated to them at least once you can just type `z dis` and it will jump you to the directory.

### Install Zoxide

Zoxide works on Mac/Linux/Windows! The project is hosted on GitHub at [zoxide](https://github.com/ajeetdsouza/zoxide). To install on Windows:

```text
winget install ajeetdsouza.zoxide
zoxide init powershell
```

The winget command does the install, the zoxide init powershell adds the line we saw above to the PowerShell profile. I cannot recommend `zoxide` enough.

### Change the order in Terminal

This is optional but if you use Windows Terminal often it's worth customizing the order that your shells are displayed in.

- Open Windows Terminal
- Click the :ChevronDownIcon: in the top menu
- Click `settings`
- Click `Open JSON FIle` at the very bottom, left of the terminal.


----------------------------------------------------------------

![screenshot](img/json.PNG)

----------------------------------------------------------------

On my Windows laptop, Windows Terminal always opens with the bottom of the terminal below the bottom of the screen. I couldn't see the Open JSON file option until dragging the window up.

Scroll down until you see

```bash
"list":
        [
            {
                "commandline": "%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                "guid": "{61c54bbd-c2c6-5271-96e7-009a87ff44bf}",
                "hidden": true,
                "name": "Windows PowerShell 7"
            },
```

Your exact JSON will be different than mine so I you might see something different. The important thing is finding `":list":` in the JSON file. Copy everything from `":list":` to the last `}` before the `]` symbol and save it to notepad++ or your favorite editor. Save a copy as a backup in case you make a mistake editing `settings.json`.

#### Move the shells

Now you can cut each shell and move it to the order you want. Notice that I renamed `Windows PowerShell` to `Windows PowShell 7` so that it's obvious which version to select.  When you are satisfied, save and close the `settings.json` file.

Notice the `"hidden": true,` and `"hidden": false,` lines. I don't know why some shells have two entries with one hidden and one not.

Here is what my final JSON looks like:

```json linenums='1' hl_lines='6 11 17 23 29 35'
        "list":
        [
            {
                "commandline": "%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
                "guid": "{61c54bbd-c2c6-5271-96e7-009a87ff44bf}",
                "hidden": true,
                "name": "Windows PowerShell 7"
            },
            {
                "guid": "{d8e96812-b789-5068-a5ae-10b2fb53e95f}",
                "hidden": false,
                "name": "Ubuntu 24.04.1 LTS",
                "source": "CanonicalGroupLimited.Ubuntu24.04LTS_79rhkp1fndgsc"
            },
            {
                "guid": "{5fb123f1-af88-5b5c-8953-d14a8def1978}",
                "hidden": false,
                "name": "PowerShell 7",
                "source": "Windows.Terminal.PowershellCore"
            },
            {
                "guid": "{2ece5bfe-50ed-5f3a-ab87-5cd4baafed2b}",
                "hidden": false,
                "name": "Git Bash",
                "source": "Git"
            },
            {
                "commandline": "%SystemRoot%\\System32\\cmd.exe",
                "guid": "{0caa0dad-35be-5f56-a8ff-afceeeaa6101}",
                "hidden": false,
                "name": "Command Prompt"
            },
            {
                "guid": "{b453ae62-4e3d-5e58-b989-0a998ec441b8}",
                "hidden": false,
                "name": "Azure Cloud Shell",
                "source": "Windows.Terminal.Azure"
            },
            {
                "guid": "{574e775e-4f2a-5b96-ac1e-a2962a402336}",
                "hidden": false,
                "name": "PowerShell",
                "source": "Windows.Terminal.PowershellCore"
            },
            {
                "guid": "{963ff2f7-6aed-5ce3-9d91-90d99571f53a}",
                "hidden": true,
                "name": "Ubuntu-24.04",
                "source": "Windows.Terminal.Wsl"
            },
            {
                "guid": "{43a35048-5e42-5c40-8a75-f5b7bfec7d65}",
                "hidden": false,
                "name": "Developer Command Prompt for VS 2019",
                "source": "Windows.Terminal.VisualStudio"
            },
            {
                "guid": "{b7ba4424-3cd0-5300-927c-57d95790a11f}",
                "hidden": false,
                "name": "Developer PowerShell for VS 2019",
                "source": "Windows.Terminal.VisualStudio"
            }
        ]
        ```
