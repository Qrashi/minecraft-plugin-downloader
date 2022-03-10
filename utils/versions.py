from __future__ import annotations

from typing import Union, Dict, Tuple

from utils.errors import report
from utils.files import pool

versions = pool.open("data/versions.json").json["versions"]


def is_valid(version: str, report_errors=False, terminate=False) -> bool:
    def error(reason, will_continue):
        if report_errors:
            if will_continue:
                report(9, "Version integrity checker", reason, additional="Program will continue despite error")
            else:
                report(9, "Version integrity checker", reason, additional="Program terminated.")
                if terminate:
                    print("Error: Version \"" + version + "\" NOT valid! Program stopped, files NOT saved.")
                    exit()

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
        else:  # Version above 1.10
            major = version[2:4]  # We only take the 11 from 1.11
            if len(version) > 4:  # Has minor version because major is at least 4 characters long
                minor = version[5:]
            else:
                minor = ""  # No minor version
        return major, minor
    if terminate:
        exit()
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
    def __init__(self, version: Union[str, Tuple[int, Union[int, str]], Dict[str, int]]):
        if type(version) is str:
            self.major, self.minor = from_string(version)
        elif type(version) is dict:
            self.major = version["major"].replace("1.", "")
            self.minor = version["minor"].replace(".", "")
        else:
            self.major = str(version[0])
            self.minor = str(version[1])

    def string(self) -> str:
        if self.minor == "":
            return "1." + str(self.major)
        return "1." + str(self.major) + "." + str(self.minor)

    def dict(self) -> dict:
        return {"major": int(self.major), "minor": _int(self.minor)}

    def matches(self, version) -> bool:
        return int(version.major) == int(self.major) and _int(version.minor) == _int(self.minor)

    def get_next_minor(self) -> Version:
        """
        Get next highest minor game version, if there is no higher minor version use the next major version
        If there is no higher main version, return current version
        :return Version: Version
        """
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
        elif int(version.major) < int(self.major):
            return True  # Other major version is lower - no need to check for minor version
        else:  # Major versions are equal
            return _int(version.minor) < _int(self.minor)  # Minor version is bigger

    def is_lower(self, version) -> bool:
        """
        Is this version lower than the specified version?
        :param version:
        :return:
        """
        if int(version.major) < int(self.major):
            return False  # Other major version is lower.
        elif int(version.major) > int(self.major):
            return True  # Other major version is higher - no need to check for minor version
        else:  # Major versions are equal
            return _int(version.minor) > _int(self.minor)  # Minor version is smaller

    def fulfills(self, requirement: VersionRangeRequirement) -> bool:
        if self.matches(requirement.minimum) or self.matches(requirement.maximum):
            return True
        return self.is_lower(requirement.maximum) and self.is_higher(
            requirement.minimum)  # Is True if MY version is lower than the maximum and MY version is higher than the minimum


class VersionRangeRequirement:
    def __init__(self, requirement: Union[Tuple[Version, Version], Dict[str, str], Dict[str, Dict[str, int]]]):
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
                # Doesnt matter if versions are dicts or strings, Version can handle both
                self.minimum = Version(requirement["min"])
                unset.pop("min")
            if "max" in requirement:
                self.maximum = Version(requirement["max"])
                unset.pop("max")
            for unset_field in unset.keys():
                if unset_field == "max":
                    self.maximum = Version("1.99.9")  # Maximum version => Supports every version
                else:
                    self.minimum = Version("1.0")  # Minimum version => Supports every version

    def string(self):
        return "Requires a version between " + self.minimum.string() + " and " + self.maximum.string()

    def dict(self):
        return {"min": self.minimum.string(), "max": self.maximum.string()}

    def matches(self, requirement: VersionRangeRequirement):
        return self.minimum.matches(requirement.minimum) and self.maximum.matches(requirement.maximum)
