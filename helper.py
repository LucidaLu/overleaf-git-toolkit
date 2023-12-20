import sys
from git import Repo
import os
from pathlib import Path
from loguru import logger

HOME_DIR = os.path.expanduser("~")
PWD_DIR = os.path.expanduser("~") + "/overleaf-git-toolkit"

GL_PATH = PWD_DIR + "/gitolite-bin/gitolite"
repo_name = "texdoc"
DROPBOX_DIR = HOME_DIR + "/Dropbox/Apps/Overleaf/"
GIT_REPO_DIR = PWD_DIR + "/" + repo_name + "/"

logger.remove()
logger.add(sys.stderr, format="{message}")


def unset_git_env():
    if "GIT_DIR" in os.environ:
        del os.environ["GIT_DIR"]


unset_git_env()

try:
    git = Repo(GIT_REPO_DIR).git
except Exception:
    print("initializing...")


def generate_key():
    from cryptography.hazmat.primitives import serialization as crypto_serialization

    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend as crypto_default_backend

    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.TraditionalOpenSSL,
        crypto_serialization.NoEncryption(),
    ).decode("utf-8")

    public_key = (
        key.public_key()
        .public_bytes(
            crypto_serialization.Encoding.OpenSSH,
            crypto_serialization.PublicFormat.OpenSSH,
        )
        .decode("utf-8")
    )

    with open("./gitolite_master_key", "w") as f:
        f.write(private_key)
    os.chmod("./gitolite_master_key", 0o600)

    with open("./gitolite_master_key.pub", "w") as f:
        f.write(public_key)


def color(text, color):
    codes = {
        "black": "0;30",
        "bright gray": "0;37",
        "blue": "1;34",
        "white": "1;37",
        "green": "1;32",
        "bright blue": "1;34",
        "cyan": "0;36",
        "bright green": "1;32",
        "red": "1;31",
        "bright cyan": "1;36",
        "purple": "0;35",
        "bright red": "1;31",
        "yellow": "0;33",
        "bright purple": "1;35",
        "dark gray": "1;30",
        "bright yellow": "1;33",
        "normal": "0",
    }
    return "\033[" + codes[color] + "m" + text + "\033[0m"


def run(args):
    import subprocess

    return subprocess.run(args, capture_output=True, text=True)


def get_intended_arch():
    with open(GIT_REPO_DIR + "ARCHIVED_LIST", "r") as f:
        intend_arch = list(
            filter(lambda x: x != "", map(lambda x: x.strip(), f.readlines()))
        )
    exlusions = []
    for prj in intend_arch:
        exlusions.append("--exclude")
        exlusions.append(prj)

    return intend_arch, exlusions


def handle_archived():
    git.fetch("--all")
    git.pull("--all")

    git.checkout("active")

    with open(GIT_REPO_DIR + "ARCHIVED_LIST", "r") as f:
        intend_arch = list(
            filter(lambda x: x != "", map(lambda x: x.strip(), f.readlines()))
        )

    git.checkout("archived")
    real_arch = list(set(os.listdir(GIT_REPO_DIR)) - {".git"})

    mv_to_arch = [prj for prj in intend_arch if prj not in real_arch]
    print("Files to be archived: ", mv_to_arch)

    if len(mv_to_arch) != 0:
        for prj in mv_to_arch:
            git.checkout("active", prj)
        git.add("--all")
        git.commit("-m", "[ARCHIVED] " + ", ".join(mv_to_arch))
    git.checkout("active")

    if len(mv_to_arch) != 0:
        for prj in mv_to_arch:
            run(["rm", "-rf", GIT_REPO_DIR + "/" + prj])
        git.add("--all")
        git.commit("-m", "[ARCHIVED] " + ", ".join(mv_to_arch))

    mv_to_active = [prj for prj in real_arch if prj not in intend_arch]
    print("Files to be activated: ", mv_to_active)

    if len(mv_to_active) != 0:
        for prj in mv_to_active:
            git.checkout("archived", prj)
        git.add("--all")
        git.commit("-m", "[ACTIVATED] " + ", ".join(mv_to_active))

    git.checkout("archived")

    if len(mv_to_active) != 0:
        for prj in mv_to_active:
            run(["rm", "-rf", GIT_REPO_DIR + "/" + prj])
        git.add("--all")
        git.commit("-m", "[ACTIVATED] " + ", ".join(mv_to_active))

    git.checkout("active")

    if len(mv_to_arch) != 0 or len(mv_to_active) != 0:
        git.push("--all")


def write_rsync_log(rsync_output):
    with open(Path.home() / "rsync.log", "a") as f:
        # write a formatted time stamp
        f.write("\n\n\n")
        import datetime

        f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        f.write("\n")
        f.write(rsync_output)


def fetch_from_dropbox():
    git.checkout("active")
    intend_arch, exlusions = get_intended_arch()

    logger.info(color("rsyncing <---- dropbox...", "blue"))
    logger.info(
        str(
            [
                "rsync",
                "-av",
                "--delete",
                "--exclude",
                ".git",
                "--exclude",
                "ARCHIVED_LIST",
            ]
            + exlusions
            + [
                DROPBOX_DIR,
                GIT_REPO_DIR,
            ]
        )
    )
    rsync_output = run(
        ["rsync", "-av", "--delete", "--exclude", ".git", "--exclude", "ARCHIVED_LIST"]
        + exlusions
        + [
            DROPBOX_DIR,
            GIT_REPO_DIR,
        ]
    ).stdout

    write_rsync_log(rsync_output)

    git.add(all=True)

    if git.status().count("Changes to be committed"):
        logger.info(
            color("update from dropbox detected, this push should be rejected", "red")
        )
        git.commit("-m", "UPDATE FROM DROPBOX")
        git.push("--all")


def push_to_dropbox():
    git.checkout("active")
    intend_arch, exlusions = get_intended_arch()

    logger.info(color("rsyncing ----> dropbox ...", "blue"))
    logger.info(
        str(
            [
                "rsync",
                "-av",
                "--delete",
                "--exclude",
                ".git",
                "--exclude",
                "ARCHIVED_LIST",
            ]
            + exlusions
            + [
                GIT_REPO_DIR,
                DROPBOX_DIR,
            ]
        )
    )
    rsync_output = run(
        ["rsync", "-av", "--delete", "--exclude", ".git", "--exclude", "ARCHIVED_LIST"]
        + exlusions
        + [
            GIT_REPO_DIR,
            DROPBOX_DIR,
        ]
    ).stdout

    write_rsync_log(rsync_output)
