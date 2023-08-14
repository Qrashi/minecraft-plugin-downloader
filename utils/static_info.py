"""
Static information for this program
"""
import datetime
import sys
from subprocess import run, PIPE

VERSION = "b2.3"
COMMIT = "could not get commit. see errors.json"

if __name__ == "__main__":
    print("This file is meant to be imported!")
    sys.exit()

try:
    commit = run("git log -n 1 --pretty=format:\"%H\"", stdout=PIPE, stderr=PIPE, shell=True, check=True)
    COMMIT = commit.stdout.decode('utf-8')
except Exception as e:
    print(f"Could not find current commit: {e}")

DAYS_SINCE_EPOCH = (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).days
