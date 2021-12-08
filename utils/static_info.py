import datetime

from requests import get

from utils.URLAccessField import URLAccessField
from .cli_provider import cli
from .errors import report
from .events import report as report_event
from .files import pool
from .versions import Version
from os import makedirs, path
from .dict_utils import enabled

if __name__ == "__main__":
    print("This file is meant to be imported!")
    exit()

DAYS_SINCE_EPOCH = (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).days
STATIC_VERSIONS = [Version("1.0")]

if pool.open("data/versions.json").json["last_check"] == 0:
    # Create "software" folder
    makedirs(path.abspath(pool.open("data/config.json").json["sources_folder"]), exist_ok=True)

if pool.open("data/versions.json").json["last_check"] == 0 or enabled(pool.open("data/config.json").json["newest_game_version"]):
    # If there has not been a last check (initialisation) will always check versions.
    if (DAYS_SINCE_EPOCH - pool.open("data/versions.json").json["last_check"]) > pool.open("data/config.json")\
                                                                                .json["version_check_interval"]:
        current_version = Version(pool.open("data/versions.json").json["current_version"])
        # The version might not exist in the versions database because the database is nonexistent!

        url_access_field = URLAccessField(pool.open("data/config.json").json["newest_game_version"])
        cli.load("Checking for new version...", vanish=True)
        try:
            response = get(url_access_field.url).json()
            versions_online = url_access_field.access(response)
            versions_json = pool.open("data/versions.json")
            versions_json.json["versions"] = []
            remote = current_version
            for version in versions_online:
                version = Version(version)  # Again, the versions database might not exist at this point
                versions_json.json["versions"].append(version.string())
                if version.is_higher(remote):
                    remote = version
                major_only = Version((version.major, "")).string()
                if major_only not in versions_json.json["versions"]:
                    versions_json.json["versions"].append(major_only)
            for static_version in STATIC_VERSIONS:
                versions_json.json["versions"].append(static_version.string())
        except Exception as e:
            report(3, "Could not fetch newest game version:", "Error while executing get request and decoding data.",
                   exception=e)
            if pool.open("data/versions.json").json["last_check"]:
                cli.fail("Error while retrieving data for first time setup, cannot continue!")
                cli.fail("This could be a config issue (see data/data_info.md -> config.json), please read the documentation.")
                print(e)
                exit()
            remote = current_version
        if current_version.matches(remote):
            pool.open("data/versions.json").json["last_check"] = DAYS_SINCE_EPOCH
        else:
            pool.open("data/versions.json").json["current_version"] = remote.string()
            if pool.open("data/versions.json").json["last_check"] == 0:
                pool.open("data/versions.json").json["last_check"] = DAYS_SINCE_EPOCH
                report_event("Initialisation", "Initialisation complete, the current minecraft version was set to " + remote.string())
                # On first initialisation. the version is 1.0 so rather give a "initialisation complete" event
                cli.success("Initialisation complete!")
                pool.sync()
                exit()
            else:
                pool.open("data/versions.json").json["last_check"] = DAYS_SINCE_EPOCH
                report_event("Game version checker", "The game version was updated to " + remote.string())
                cli.success("Fetched new minecraft version: " + remote.string())
