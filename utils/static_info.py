import datetime
import sys
from os import makedirs, path
from subprocess import run, PIPE

from utils.file_defaults import CONFIG

VERSION = "b2.0-rc1"
COMMIT = "could not get commit. see errors.json"

from .files import pool

if __name__ == "__main__":
    print("This file is meant to be imported!")
    sys.exit()

commit = run("git log -n 1 --pretty=format:\"%H\"", stdout=PIPE, stderr=PIPE, shell=True)
if commit.returncode != 0:
    print("Could not find current commit.")
else:
    COMMIT = commit.stdout.decode('utf-8')

DAYS_SINCE_EPOCH = (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).days

if pool.open("data/versions.json").json["last_check"] == 0:
    # Create "software" folder
    makedirs(path.abspath(pool.open("data/config.json", default=CONFIG).json["sources_folder"]), exist_ok=True)

