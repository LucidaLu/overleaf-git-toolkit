from helper import *

generate_key()

print("master key generated.")

os.makedirs(HOME_DIR + "/.ssh/", exist_ok=True)
with open(HOME_DIR + "/.ssh/config", "a") as f:
    f.write(
        f"""
Host local-gitolite
    User {os.environ['USER']}
    HostName localhost
    IdentityFile {PWD_DIR}/gitolite_master_key
    IdentitiesOnly yes
"""
    )

run(["mkdir", "gitolite-bin"])

run(["gitolite/install", "-to", PWD_DIR + "/gitolite-bin"])

run([GL_PATH, "setup", "-a", "dummy"])

os.mkdir(HOME_DIR + "/.gitolite/keydir/")

run(["rm", "-rf", HOME_DIR + "/repositories/gitolite-admin.git"])

run(["rm", "-rf", HOME_DIR + "/repositories/testing.git"])

run(["cp", "./.gitolite.rc", HOME_DIR + "/.gitolite.rc"])

with open("./.gitolite.rc", "r") as f:
    rc = f.read()
with open(HOME_DIR + "/.gitolite.rc", "w") as f:
    f.write(rc.replace("{{working_dir}}", PWD_DIR))

with open(HOME_DIR + "/.gitolite/conf/gitolite.conf", "w") as f:
    f.write(
        f"""repo {repo_name}
    RW+     =   gitolite_master_key
    RW active    =   self
    R archived    =   self
"""
    )

run(["cp", "./pubkey", HOME_DIR + "/.gitolite/keydir/self.pub"])
run(
    [
        "cp",
        PWD_DIR + "/gitolite_master_key.pub",
        HOME_DIR + "/.gitolite/keydir/gitolite_master_key.pub",
    ]
)

run([GL_PATH, "compile"])
run([GL_PATH, "trigger", "POST_COMPILE"])
run([GL_PATH, "setup", "-ho"])


import sys

EXEC_FLAG = "#!" + sys.executable + "\n"
INCLUDE_PATH = f"""import sys
sys.path.append("{PWD_DIR}")
"""

with open("./pre-git", "r") as f:
    cmd = f.read()

with open("./gitolite-bin/triggers/pre-git", "w") as f:
    f.write(EXEC_FLAG + INCLUDE_PATH + cmd)
os.system("chmod u+x " + PWD_DIR + "/gitolite-bin/triggers/pre-git")


with open("./post-update", "r") as f:
    cmd = f.read()

os.makedirs(PWD_DIR + "/hooks/common", exist_ok=True)

DB_FL_HOOK = PWD_DIR + "/hooks/common/post-update"
with open(DB_FL_HOOK, "w") as f:
    f.write(EXEC_FLAG + INCLUDE_PATH + cmd)
os.system("chmod u+x " + DB_FL_HOOK)


from subprocess import Popen

print("cloning git repo...")
with open("/dev/null", "w") as output:
    Popen(
        [
            "git",
            "clone",
            f"local-gitolite:{repo_name}",
        ],
        cwd=PWD_DIR,
        stdout=output,
        stderr=output,
    ).communicate()

unset_git_env()
git = Repo(GIT_REPO_DIR).git

print("setting up repo...")

run(["touch", GIT_REPO_DIR + "ARCHIVED_LIST"])
git.add("--all")
git.commit("-m", "initial commit")

git.branch("-m", "master", "active")
git.push("-u", "origin", "active")
run(["ssh", "local-gitolite", "symbolic-ref", repo_name, "refs/head/active"])

# git.push("origin", "--delete", "master")
git.checkout("--orphan", "archived")
run(["rm", GIT_REPO_DIR + "ARCHIVED_LIST"])
git.add("--all")
git.commit("-m", "empty commit", "--allow-empty")
git.push("-u", "origin", "archived")

git.checkout("active")

print("sync files from dropbox...")

run(
    [
        "rsync",
        "-av",
        DROPBOX_DIR,
        GIT_REPO_DIR,
    ]
)

git.add("--all")
git.commit("-m", "initial sync from dropbox")
git.push()

print("setup complete.")
print("you may now git clone -b active server:repo on your local machine")


run([GL_PATH, "setup", "-ho"])