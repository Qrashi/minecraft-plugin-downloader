"""
Minecraft version utilities
"""
from __future__ import annotations

import os
import sys
from os import makedirs, path

from typing import Union, Dict, Tuple

from singlejson import load, sync
import utils.cli as cli
from utils.context_manager import context
from utils.errors import report
from utils.events import report as report_event
from utils.file_defaults import CONFIG, VERSIONS
from utils.static_info import DAYS_SINCE_EPOCH

versions = load("data/versions.json", default=VERSIONS).json
config = load("data/config.json", default=CONFIG).json


def report_malformed_version(version: str, verbose: bool = True) -> bool:
    """
    Report a malformed version (check if the malformed version should be reported)
    :param verbose:
    :param version: Version to check -& report
    :return: if version is not malformed
    """
    if version in versions["known_malformed_versions"]:
        return True
    if "w" in version and len(version) == 6 and version[0].isdigit() and int(version[0]) < 4:
        # snapshot version
        return True
    if len(version) == 10 and "-rc" in version:
        # release candidate version
        return True
    if len(version) == 11 and "-pre" in version:
        # prerelease version
        return True
    if not verbose:
        return False
    if is_valid(version[:4], verbose=False) or report_malformed_version(version[:6], verbose=False):
        return True
    cli.fail(f"Malformed version \"{version}\" retrieved!")
    report(9, "version integrity checker", f"{version} is malformed! {context.name} - {context.task}")
    return False


def is_valid(version: str, verbose: bool = True) -> bool:
    """
    Check if a string version description is valid
    :param version: Version to check for validity
    :return: Weather or not string is a valid version
    """

    version = str(version)
    if len(version) > 7:  # Longer than 1.17.77 (6)
        if verbose: report_malformed_version(version, verbose=verbose)
        return False
    if len(version) < 3:  # Shorter than 1.1 (3)#
        if verbose: report_malformed_version(version, verbose=verbose)
        return False
    if version[:2] != "1.":  # Minecraft 2.x when?
        if verbose: report_malformed_version(version, verbose=verbose)
        return False
    return True


def from_string(version: str, verbose: bool = True) -> tuple[str, str]:
    """
    Split major and minor versions into two strings
    :param version: Version to split
    :return: a tuple with both the minor and major version as a strings
    """
    if is_valid(version, verbose=verbose):
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
    else:
        return "1", "0"


def _int(string: str):
    """
    Special to int conversion, used for minor versions, a "" minor version has the value 0
    :param string:
    :return:
    """
    if string == "":
        return 0
    return int(string)

_not_found_version: Version = None


class Version:
    """
    A minecraft version
    """
    default = _not_found_version

    def __init__(self, version: Union[str, Tuple[Union[int, str], Union[int, str]], Dict[str, int]], verbose: bool = True):
        """
        Initialize a new version object
        :param version: version to construct
        """
        if type(version) is str:
            self.major, self.minor = from_string(version, verbose=verbose)
        elif type(version) is dict:
            self.major = version["major"].replace("1.", "")
            self.minor = version["minor"].replace(".", "")
        else:
            self.major = str(version[0])
            self.minor = str(version[1])
        if config["debug"]:
            cli.info(f"Version {version} was parsed as version {self.string()} - {context.name}")


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
        if attempt.string() in versions["versions"]:
            return attempt
        # There is no next major version
        return self.get_next_major()

    def get_next_major(self) -> Version:
        """
        Get next highest major game version, if there is no higher minor version use the current version
        :return Version: Version
        """
        attempt = Version((str(int(self.major) + 1), ""))
        if attempt.string() in versions["versions"]:
            return attempt
        attempt = Version((str(int(self.major) + 1), 1))
        if attempt.string() in versions["versions"]:
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
        return f"Requires a version between {self.minimum.string()} and {self.maximum.string()}"

    def short_string(self):
        """
        Generate a short human-readable string
        :return: human-readable string
        """
        return f"{self.minimum.string()} - {self.maximum.string()}"

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
    _not_found_version = Version.default
    from utils.access_fields import WebAccessField
    context.task = "checking for new game versions"
    context.failure_severity = 3
    context.name = "main"
    config = load("data/config.json", default=CONFIG).json

    if versions["last_check"] == 0:
        # Initialize updater
        folder = config["sources_folder"]
        makedirs(path.abspath(folder), exist_ok=True)
        cli.success(f"Created software folder at {folder}")

    if versions["last_check"] == 0 or (DAYS_SINCE_EPOCH - versions["last_check"]) > config["version_check_interval"]:
        cli.loading("Checking for newest versions...", vanish=True)
        current_highest = Version(versions["current_version"])

        retrieved_version_data = WebAccessField(config["newest_game_version"]).execute({})
        if isinstance(retrieved_version_data, Exception):
            cli.fail(f"Could not retrieve newest game version online ({retrieved_version_data})")
            if load("data/versions.json").json["last_check"]:
                cli.fail("Error while retrieving data for first time setup, cannot continue!")
                cli.fail(
                    "This could be a config issue (see data/data_info.md -> config.json), please read the documentation.")
                print(retrieved_version_data)
                sys.exit()

        updated = False
        highest = current_highest
        if type(retrieved_version_data) is list:
            for version in retrieved_version_data:
                version = Version(version)
                if version.matches(Version.default):
                    continue
                if version.string() not in versions["versions"]:
                    versions["versions"].append(version.string())
                    updated = True
                if version.is_higher(highest):
                    highest = version
        else:
            version = Version(retrieved_version_data)
            if version.matches(Version.default)
            if version.string() not in versions["versions"]:
                versions["versions"].append(version.string())
                updated = True
                if version.is_higher(current_highest):
                    highest = version

        if versions["last_check"] == 0:
            versions["last_check"] = DAYS_SINCE_EPOCH
            versions["current_version"] = highest.string()
            report_event("Initialisation", "Current minecraft version" + highest.string())
            cli.success("Initialisation complete!")
            sync()
            sys.exit()

        versions["last_check"] = DAYS_SINCE_EPOCH
        versions["current_version"] = highest.string()
        if updated:
            report_event("Game version checker",
                         f"Retrieved new game versions. New highest version: {highest.string()}")
            if current_highest.matches(highest):
                cli.success("Fetched new minecraft version(s)!")
            else:
                cli.success(f"Fetched new minecraft version(s): {highest.string()}")
