# Functionality

1. Git push and pull from overleaf.
2. New locally created folder will appear as new project in overleaf.
3. Add folder name to `ARCHIVED_LIST` to move it to `archived` branch. Archived branch will not be synced with dropbox.

# Tips
1. Default branch name is `active`.
2. Don't modify `archived` branch. It is unreasonable and you will not be able to push the changes.

# Setup

## client side
1. Generate a new key pair for `gitolite`. Must be different from the one used for ssh.
2. Edit `~/.ssh/config` and append the following entry:
```
Host gitolite
  User [user name on the server]
  HostName [address of the server]
  IdentityFile ~/.ssh/[you new generated private key]
  IdentitiesOnly yes
```

## server side
1. Setup [dropbox-headless](https://www.dropbox.com/install-linux).
2. Clone this project. Write your newly generated key in `pubkey`.
3. Modify contents in `install.py`.
4. `python install.py`.


# Usage

Run 
```
git clone -b active gitolite:texdoc
```
