import datetime
import sys
from subprocess import run, PIPE

VERSION = "b2.0"
COMMIT = "could not get commit. see errors.json"

if __name__ == "__main__":
    print("This file is meant to be imported!")
    sys.exit()

commit = run("git log -n 1 --pretty=format:\"%H\"", stdout=PIPE, stderr=PIPE, shell=True)
if commit.returncode != 0:
    print("Could not find current commit.")
else:
    COMMIT = commit.stdout.decode('utf-8')

DAYS_SINCE_EPOCH = (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).days

