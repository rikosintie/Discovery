# Using PowerShell

Here are the steps I took to get Windows terminal installed and the latest version of PowerShell configured with history and some other Linux like features.

## Getting Started

The first step is installing the Windows Terminal. While not strictly required, you could use the cmd.exe shell, I find the Windows Terminal a much better solution. It allows:

Multiple applications in one application
    - PowerShell
    - WSL
    - Git Bash
    - CMD.exe



### Install the latest version of PowerShell core

Windows 11 ships with PowerShell 5.1 installed. I don't understand all the reasons behind it, but PowerShell 7.5 is the latest version and it installs BESIDE PowerShell 5.1. That is really confusing and both versions store there `$PROFILE` in separate locations!
