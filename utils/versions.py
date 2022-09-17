"""
Minecraft version utilities
"""
from __future__ import annotations
import sys
from os import makedirs, path

from typing import Union, Dict, Tuple

from utils.cli_provider import cli
from utils.access_fields import WebAccessField
from utils.context_manager import context
from utils.dict_utils import enabled
from utils.errors import report
from utils.events import report as report_event
from utils.file_defaults import CONFIG
from utils.files import pool
from utils.static_info import DAYS_SINCE_EPOCH

versions = pool.open("data/versions.json").json["versions"]


def is_valid(version: str, report_errors=False, terminate=False) -> bool:
    """
    Check if a string version description is valid
    :param version: Version to check for validity
    :param report_errors: weather to report non-compliance to validity rules
    :param terminate: weather to terminate program on non-compliance to validity rules
    :return: Weather or not string is a valid version
    """
    def error(reason, will_continue):
        if report_errors:
            if will_continue:
                report(9, "Version integrity checker", reason, additional="Program will continue despite error")
            else:
                report(9, "Version integrity checker", reason, additional="Program terminated.")
                if terminate:
                    print("Error: Version \"" + version + "\" NOT valid! Program stopped, files NOT saved.")
                    sys.exit()

    version = str(version)
    if len(version) > 7:  # Longer than 1.17.77 (6)
        error(version + " is too long!", False)
        return False
    if len(version) < 3:  # Shorter than 1.1 (3)#
        error(version + " is too short!", False)
        return False
    if version[:2] != "1.":  # Minecraft 2.x when?
        error(version + " does not have the usual \"1.\" pre clause", False)
        return False
    if not version[3:].isdigit():
        error(version + " is not only numbers and dots!", False)
    return True


def from_string(version: str, report_errors=False, terminate=False) -> tuple[str, str]:
    """
    Split major and minor versions into two strings
    :param version: Version to split
    :param report_errors: weather to report non-compliance to validity rules
    :param terminate: weather to terminate program on non-compliance to validity rules
    :return: a tuple with both the minor and major version as a strings
    """
    version = version.replace("-pre", "")
    if is_valid(version, report_errors=report_errors, terminate=terminate):
        if len(version) <= 3:
            major = version[2]  # We only take the 9 from 1.9
            if len(version) > 3:  # Has minor version because major is at least (1.9)
                minor = version[4:]  # We only take the 8 from 1.9.8
            else:
                minor = ""  # No minor version
            return major, minor
        if version[3] == '.':  # Version under 1.10
            major = version[2]  # We only take the 9 from 1.9
            if len(version) > 3:  # Has minor version because major is at least (1.9)
                minor = version[4:]  # We only take the 8 from 1.9.8
            else:
                minor = ""  # No minor version
            return major, minor
        major = version[2:4]  # We only take the 11 from 1.11
        if len(version) > 4:  # Has minor version because major is at least 4 characters long
            minor = version[5:]
        else:
            minor = ""  # No minor version
        return major, minor
    if terminate:
        sys.exit()
    else:
        return "", ""


def _int(string: str):
    """
    Special to int conversion, used for minor versions, a "" minor version has the value 0
    :param string:
    :return:
    """
    if string == "":
        return 0
    return int(string)


class Version:
    """
    A minecraft version
    """
    def __init__(self, version: Union[str, Tuple[Union[int, str], Union[int, str]], Dict[str, int]]):
        """
        Initialize a new version object
        :param version: version to construct
        """
        if type(version) is str:
            self.major, self.minor = from_string(version)
        elif type(version) is dict:
            self.major = version["major"].replace("1.", "")
            self.minor = version["minor"].replace(".", "")
        else:
            self.major = str(version[0])
            self.minor = str(version[1])

    def string(self) -> str:
        """
        Convert version into string
        :return: converted string
        """
        if self.minor == "":
            return "1." + str(self.major)
        return "1." + str(self.major) + "." + str(self.minor)

    def matches(self, version) -> bool:
        """
        Check if version is equal to another
        :param version: other version
        :return: equality of versions
        """
        return int(version.major) == int(self.major) and _int(version.minor) == _int(self.minor)

    def get_next_minor(self) -> Version:
        """
        Get next highest minor game version, if there is no higher minor version use the next major version
        If there is no higher main version, return current version
        :return Version: Version
        """
        if self.minor == '':
            attempt = Version((self.major, "1"))
        else:
            attempt = Version((self.major, str(int(self.minor) + 1)))
        if attempt.string() in versions:
            return attempt
        # There is no next major version
        return self.get_next_major()

    def get_next_major(self) -> Version:
        """
        Get next highest major game version, if there is no higher minor version use the current version
        :return Version: Version
        """
        attempt = Version((str(int(self.major) + 1), ""))
        if attempt.string() in versions:
            return attempt
        attempt = Version((str(int(self.major) + 1), 1))
        if attempt.string() in versions:
            return attempt
        return self

    def is_higher(self, version) -> bool:
        """
        Is this version higher than the specified version?
        :param version:
        :return:
        """
        if int(version.major) > int(self.major):
            return False  # Other major version is higher.
        if int(version.major) < int(self.major):
            return True  # Other major version is lower - no need to check for minor version
        return _int(version.minor) < _int(self.minor)  # Minor version is bigger

    def is_lower(self, version) -> bool:
        """
        Is this version lower than the specified version?
        :param version:
        :return:
        """
        if int(version.major) < int(self.major):
            return False  # Other major version is lower.
        if int(version.major) > int(self.major):
            return True  # Other major version is higher - no need to check for minor version
        return _int(version.minor) > _int(self.minor)  # Minor version is smaller

    def fulfills(self, requirement: VersionRangeRequirement) -> bool:
        """
        Check if version fulfills VersionRangeRequirement
        :param requirement: requirement to check against
        :return: weather or not the version complies to the rules of the VersionRangeRequirement
        """
        if self.matches(requirement.minimum) or self.matches(requirement.maximum):
            return True
        return self.is_lower(requirement.maximum) and self.is_higher(
            requirement.minimum)  # Is True if MY version is lower than the maximum and MY version is higher than the minimum


class VersionRangeRequirement:
    """
    A Version requirement
    """
    def __init__(self, requirement: Union[Tuple[Version, Version], Dict[str, str], Dict[str, Dict[str, int]]]):
        """
        Initialize a new Version requirement
        :param requirement: requirement data (tuple of required versions)
        """
        if type(requirement) is tuple:
            if type(requirement[0]) is str:
                # two string versions
                self.minimum = Version(requirement[0])
                self.maximum = Version(requirement[1])
            else:
                # Just two versions, plan old "from to"
                self.minimum = requirement[0]
                self.maximum = requirement[1]
        else:
            unset = {"min": None, "max": None}
            if "min" in requirement:  # min in dict > definitively a valid dict
                # Doesn't matter if versions are dicts or strings, Version can handle both
                self.minimum = Version(requirement["min"])
                unset.pop("min")
            if "max" in requirement:
                self.maximum = Version(requirement["max"])
                unset.pop("max")
            for unset_field in unset:
                if unset_field == "max":
                    self.maximum = Version("1.99.9")  # Maximum version => Supports every version
                else:
                    self.minimum = Version("1.0")  # Minimum version => Supports every version

    def string(self):
        """
        Generate a human-readable string
        :return: human-readable string
        """
        return "Requires a version between " + self.minimum.string() + " and " + self.maximum.string()

    def dict(self):
        """
        Return range requirement as a dict
        :return: range requirement as a dictionary
        """
        return {"min": self.minimum.string(), "max": self.maximum.string()}

    def matches(self, requirement: VersionRangeRequirement):
        """
        Check if requirements are equal
        :param requirement: other requirement
        :return: state of equality
        """
        return self.minimum.matches(requirement.minimum) and self.maximum.matches(requirement.maximum)


def check_game_versions():
    """
    Check for new game versions
    :return:
    """
    if pool.open("data/versions.json").json["last_check"] == 0:
        # Create "software" folder
        makedirs(path.abspath(pool.open("data/config.json", default=CONFIG).json["sources_folder"]), exist_ok=True)
    if pool.open("data/versions.json").json["last_check"] == 0 or enabled(
            pool.open("data/config.json", default=CONFIG).json["newest_game_version"]):
        # If there has not been a last check (initialisation) will always check versions.
        if (DAYS_SINCE_EPOCH - pool.open("data/versions.json").json["last_check"]) > \
                pool.open("data/config.json", default=CONFIG).json["version_check_interval"]:
            current_version = Version(pool.open("data/versions.json").json["current_version"])
            # The version might not exist in the versions database because the database is nonexistent!
            context.name = "main"
            context.task = "fetching newest game versions"
            context.failure_severity = 3

            cli.load("Checking for new version...", vanish=True)
            versions_online = WebAccessField(
                pool.open("data/config.json", default=CONFIG).json["newest_game_version"]).execute({})
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
                    # On first initialisation. the version is 1.0 so rather give an "initialisation complete" event
                    cli.success("Initialisation complete!")
                    pool.sync()
                    sys.exit()
                else:
                    pool.open("data/versions.json").json["last_check"] = DAYS_SINCE_EPOCH
                    report_event("Game version checker", "The game version was updated to " + highest.string())
                    cli.success("Fetched new minecraft version(s): " + highest.string())
