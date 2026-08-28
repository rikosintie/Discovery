# GitHub over SSH — one-time setup per machine

Push/pull to GitHub without ever typing a username or a Personal Access
Token. The SSH key's passphrase is unlocked once per login by the GNOME
Keyring agent — the same "unlock the keychain" feel as VS Code.

Tested on Linux (GNOME/Wayland, zsh, VS Code as a Flatpak).

---

## Why bother

An `https://github.com/...` remote asks for a username + PAT on every
push. Git's default `cache` credential helper only holds that in memory
for 15 minutes (`credential.helper = cache --timeout 900`), so it feels
like a fresh login every time. Switching the remote to SSH removes
credentials from the loop entirely.

---

## 1. Make an SSH key (skip if you already have one for GitHub)

```bash
ssh-keygen -t ed25519 -C "michael.hubbard999@gmail.com" -f ~/.ssh/id_github
```

- Give it a passphrase when prompted (the keyring will remember it).
- This creates `~/.ssh/id_github` (private) and `~/.ssh/id_github.pub`
  (public).

Check whether a key already exists:

```bash
ls ~/.ssh/id_github ~/.ssh/id_ed25519 ~/.ssh/id_rsa 2>/dev/null
```

## 2. Add the public key to GitHub

```bash
cat ~/.ssh/id_github.pub
```

Copy the whole line, then go to <https://github.com/settings/keys> →
**New SSH key**:

- **Key type:** `Authentication Key` (not "Signing Key").
- **Title:** something that names the machine, e.g. `dev-laptop-2`.
- **Key:** paste the line.

## 3. Point SSH at the key

Edit `~/.ssh/config` (create it if missing) so it has:

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_github
    IdentitiesOnly yes
```

`IdentitiesOnly yes` stops ssh from offering every other key in
`~/.ssh/` first (which can trip GitHub's "too many auth failures").

## 4. Test

```bash
ssh -T git@github.com
```

- First time: answer `yes` to the host-authenticity prompt.
- Enter the key passphrase if asked.
- Success looks like:
  `Hi <username>! You've successfully authenticated, but GitHub does not
  provide shell access.`

If it says `Permission denied (publickey)`, the public key didn't land on
GitHub or `~/.ssh/config` isn't pointing at the right key. Diagnose with
`ssh -vT git@github.com`.

## 5. Switch the repo's remote to SSH

Inside the repo:

```bash
git remote set-url origin git@github.com:rikosintie/Discovery.git
git remote -v          # both lines should show git@github.com:...
git fetch origin       # silent success = done
```

Or clone fresh with the SSH URL:

```bash
git clone git@github.com:rikosintie/Discovery.git
```

## 6. Cache the passphrase for the session

```bash
ssh-add ~/.ssh/id_github
```

On GNOME the login keyring runs the SSH agent (`SSH_AUTH_SOCK` points at
`/run/user/<uid>/keyring/ssh`), so it remembers the key across reboots
after the first unlock. `ssh-add -l` lists what's currently loaded.

## 7. Optional: drop the credential helper that was forgetting logins

```bash
git config --global --unset credential.helper
```

Only affects HTTPS remotes, which you're no longer using for this repo.

---

## Notes

- **VS Code as a Flatpak (`com.visualstudio.code`)** works with this
  as-is: its manifest already grants `--socket=ssh-auth` and full host
  filesystem access, and it sets `SSH_AUTH_SOCK=/keyring/ssh` inside the
  sandbox, so it shares the same GNOME Keyring agent as the terminal.
  Just make sure the key is loaded (`ssh-add`) and commit/push from the
  Source Control panel as normal. The GitHub "Sign in" (for PRs/issues)
  is a separate API token and is unaffected.
- **`gh-pages` forced-update messages** on `git fetch` are just GitHub's
  Pages build bot republishing the docs site. They only touch
  `origin/gh-pages`, never `main`. Ignore them.
- **Per-machine:** steps 1–4 and 6 are per machine; step 5 is per clone.
  The same public key can be added to GitHub from several machines, or
  give each machine its own key (easier to revoke one later).
