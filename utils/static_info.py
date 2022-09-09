import datetime
import sys
from os import makedirs, path
from subprocess import run, PIPE

VERSION = "b2.0-rc1"
COMMIT = "could not get commit. see errors.json"

from utils.access_fields import WebAccessField
from .cli_provider import cli
from .dict_utils import enabled
from .events import report as report_event
from .files import pool
from .versions import Version
from .context_manager import context


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
    makedirs(path.abspath(pool.open("data/config.json").json["sources_folder"]), exist_ok=True)

if pool.open("data/versions.json").json["last_check"] == 0 or enabled(
        pool.open("data/config.json").json["newest_game_version"]):
    # If there has not been a last check (initialisation) will always check versions.
    if (DAYS_SINCE_EPOCH - pool.open("data/versions.json").json["last_check"]) > pool.open("data/config.json") \
            .json["version_check_interval"]:
        current_version = Version(pool.open("data/versions.json").json["current_version"])
        # The version might not exist in the versions database because the database is nonexistent!
        context.software = "main"
        context.task = "fetching newest game versions"
        context.failure_severity = 3

        cli.load("Checking for new version...", vanish=True)
        versions_online = WebAccessField(pool.open("data/config.json").json["newest_game_version"]).execute({})
        if isinstance(versions_online, Exception):
            cli.fail(f"Could not retrieve newest game version online ({versions_online})")
            if pool.open("data/versions.json").json["last_check"]:
                cli.fail("Error while retrieving data for first time setup, cannot continue!")
                cli.fail(
                    "This could be a config issue (see data/data_info.md -> config.json), please read the documentation.")
                print(versions_online)
                sys.exit()

        versions_json = pool.open("data/versions.json").json
        if type(versions_online) is list:
            highest = Version("1.0")
            for version in versions_online:
                version = Version(version)
                if version.string() not in versions_json["versions"]:
                    versions_json["versions"].append(version.string())
                if version.is_higher(highest):
                    highest = version
        else:
            highest = Version(versions_online)
            versions_json["versions"].append(highest.string())

        if current_version.matches(highest):
            pool.open("data/versions.json").json["last_check"] = DAYS_SINCE_EPOCH
        else:
            pool.open("data/versions.json").json["current_version"] = highest.string()
            if pool.open("data/versions.json").json["last_check"] == 0:
                pool.open("data/versions.json").json["last_check"] = DAYS_SINCE_EPOCH
                report_event("Initialisation",
                             "Initialisation complete, the current minecraft version was set to " + highest.string())
                # On first initialisation. the version is 1.0 so rather give a "initialisation complete" event
                cli.success("Initialisation complete!")
                pool.sync()
                sys.exit()
            else:
                pool.open("data/versions.json").json["last_check"] = DAYS_SINCE_EPOCH
                report_event("Game version checker", "The game version was updated to " + highest.string())
                cli.success("Fetched new minecraft version(s): " + highest.string())
