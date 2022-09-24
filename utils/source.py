"""
Source management tools
"""
import datetime
import sys
from os import remove, makedirs
from shutil import copy, rmtree
from typing import Union, Dict

from requests import get

import utils.cli as cli
from .access_fields import WebAccessField
from .context_manager import context
from .dict_utils import enabled
from .errors import report
from .events import report as report_event
from .file_defaults import CONFIG
from singlejson import load
from .io import abs_filename
from .tasks import execute
from .versions import Version, VersionRangeRequirement

SOURCES_DIR = load("data/config.json", default=CONFIG).json["sources_folder"]


class Source:
    """
    A source can retrieve the newest builds for a given software
    """

    def __init__(self, software: str):
        """
        Initialize source
        :param software: name of relevant software
        """
        sources = load("data/sources.json", default="{}").json
        if software not in sources:
            report(9, "source class", "Typo in config: Could not find specified source, terminating!",
                   additional="Provided source: " + software)
            sys.exit()

        source_info = sources[software]
        self.name = software
        self.server = source_info["server"]
        self.last_check = source_info["last_checked"]
        self.config: dict = source_info
        all_software = load("data/software.json", default="{}").json

        if "headers" in self.config:
            self.headers = self.config["headers"]
        else:
            self.headers = load("data/config.json", default=CONFIG).json["default_headers"]

        self.severity = all_software[software]["severity"]
        self.file = all_software[software]["file"]

        requirement = VersionRangeRequirement(all_software[self.name]["requirements"])
        version_to_use = requirement.maximum

        self.replaceable: Dict[str, str] = {
            "%newest_version%": version_to_use.string(),
            "%newest_major%": f"1.{version_to_use.major}",
            "%newest_minor%": f".{version_to_use.minor}",
            "%build%": self.config["build"]["local"]
        }

    def replace(self, string: str) -> str:
        """
        Replace variables marked with %name% with their data
        :param string: sting to perform replacement on
        :return: string with inserted data
        """
        result = string
        for this, that in self.replaceable.items():
            result = result.replace(this, that)
        return result

    def check_compatibility(self):
        """
        Check for updates to software compatibility
        :return:
        """
        context.task = "updating compatibility"
        new_compatibility = WebAccessField(self.config["compatibility"]["remote"]).execute(self.replaceable, headers=self.headers)
        if isinstance(new_compatibility, Exception):
            cli.fail("Could not retrieve newest compatibility: " + str(new_compatibility))
            return None

        all_software = load("data/software.json", default="{}").json
        previous_compatibility = VersionRangeRequirement(all_software[self.name]["requirements"])

        if type(new_compatibility) is str:
            newest = Version(new_compatibility)
            lower_newest = Version(new_compatibility)
            if self.config["compatibility"]["behaviour"].endswith("|major"):
                newest = Version((newest.major, "99"))
                lower_newest = Version((newest.major, ""))
            if self.config["compatibility"]["behaviour"].startswith("extend|"):
                compatibility = VersionRangeRequirement((previous_compatibility.minimum, newest))
            else:  # precise mode
                compatibility = VersionRangeRequirement((lower_newest, newest))
        elif type(new_compatibility) is list:
            if len(new_compatibility) == 0:
                report(self.severity, "compatibility checker",
                       f"{self.name} has NO compatibilities (list is empty) ({new_compatibility})",
                       software=self.name)
                cli.fail("Could not fetch compatibility for " + self.name + " - no compatibilities found!")
                return None

            # Retrieve newest and oldest version
            newest = Version("1.0")
            for version in new_compatibility:
                version_obj = Version(version)
                if version_obj.is_higher(newest):
                    newest = version_obj
            # Retrieve lowest
            lowest = newest
            for version in new_compatibility:
                version_obj = Version(version)
                if version_obj.is_lower(lowest):
                    lowest = version_obj
            maxed_newest = newest
            if self.config["compatibility"]["behaviour"].endswith("|major"):
                maxed_newest = Version((newest.major, "99"))
            if self.config["compatibility"]["behaviour"].startswith("max|"):
                if self.config["compatibility"]["behaviour"].endswith("|major"):  # all the max major
                    compatibility = VersionRangeRequirement(
                        (Version((maxed_newest.major, "")), maxed_newest))  # Major version compatible
                else:
                    compatibility = VersionRangeRequirement((maxed_newest, maxed_newest))
            elif self.config["compatibility"]["behaviour"].startswith("extend|"):
                compatibility = VersionRangeRequirement(
                    (previous_compatibility.minimum, maxed_newest))  # Previous version compatible
            else:
                # Must be "all"
                compatibility = VersionRangeRequirement((lowest, maxed_newest))
        else:
            report(self.severity, "Compatibility checker",
                   "Compatibility is not of type array or string! type: " + str(type(new_compatibility)),
                   software=self.name, additional="recieved compatibility: " + str(new_compatibility))
            cli.fail(
                "Could not fetch compatibility for " + self.name + " - no list of compatibilities or compatibility found!")
            return None

        if not previous_compatibility.matches(compatibility):
            all_software[self.name]["requirements"] = compatibility.dict()
            cli.success("Detected version compatibility increment for " + self.name + "!")
            report_event("Compatibility checker",
                         "Compatibility for " + self.name + " has been changed to " + compatibility.string() + "!")

        self.replaceable["%newest_version%"] = compatibility.maximum.string()
        self.replaceable["%newest_major%"] = f"1.{compatibility.maximum.major}"
        self.replaceable["%newest_minor%"] = f".{compatibility.minimum.minor}"
        return None

    def get_newest_build(self) -> Union[int, str]:
        """
        Get the newest buildID from the corresponding build server
        :return: buildID (str, int)
        """
        if not enabled(self.config["build"]):
            return self.config["build"]["local"]
        context.task = "retrieving newest build"
        buildID = WebAccessField(self.config["build"]["remote"]).execute(self.replaceable, headers=self.headers)
        if isinstance(buildID, Exception):
            cli.fail(f"Could not retrieve newest buildID for {self.name} - {buildID}!")
            return self.config["build"]["local"]
            # Return same build, don't do anything

        if type(buildID) is str or type(buildID) is int:
            load("data/sources.json", default="{}").json[self.name]["last_checked"] = datetime.datetime.now().strftime(
                "%m.%d %H:%M")
            # Single newest build
            return buildID
        if type(buildID) is list:
            # List of builds MUST be ints to compare
            if len(buildID) == 0:
                # No builds!
                cli.fail(
                    f"Could not fetch latest build for {self.name}, there are no builds (list of builds is empty)")
                report(self.severity, "download - " + self.name, f"List of builds is EMPTY ({buildID})",
                       software=self.name)
            if len(buildID) == 1:
                load("data/sources.json", default="{}").json[self.name]["last_checked"] = datetime.datetime.now().strftime(
                    "%m.%d %H:%M")
                return int(buildID[0])
            builds = []
            for build in buildID:
                if type(build) is not int:
                    if build.isdigit():
                        build = int(build)
                    else:
                        report(int(self.severity / 2), f"retrieving newest version for {self.name}",
                               "a build in the list of buildIDs is not convertible to int. update may have gone undetected.",
                               software=self.name)
                        continue
                builds.append(build)
            load("data/sources.json", default="{}").json[self.name]["last_checked"] = datetime.datetime.now().strftime(
                "%m.%d %H:%M")
            return max(builds)
        # Unknown version type
        cli.fail(f"Could not retrieve valid buildID for {self.name} (unknown type)")
        report(self.severity, f"download - {self.name}", f"retrieved buildID is not usable: {buildID}!",
               software=self.name)
        return self.config["build"]["local"]

    def download_build(self) -> bool:
        """
        Downlaod the newest build and put it into the software directory
        :return: Weather or not the download has been successful
        """
        context.task = "downloading newest build"
        url = WebAccessField(self.config["build"]["download"]).execute(self.replaceable, headers=self.headers)
        if isinstance(url, Exception):
            cli.fail(f"Could not retrieve newest download URL for {self.name}: {url}")
            return False
        try:
            response = get(url, stream=True, allow_redirects=True, headers=self.headers)
        except Exception as e:
            cli.fail(f"Error while downloading {self.name} from {self.server}: {e}")
            report(self.severity, f"download - {self.name}", "exception occurred while downloading!",
                   software=self.name, exception=e, additional=f"URL: {url}")
            return False
        if response.status_code != 200:
            cli.fail(f"Error while downloading {self.name} from {self.server} - status code {response.status_code}!")
            report(self.severity, f"download - {self.name}",
                   f"Download finished with code {response.status_code}",
                   software=self.name, additional=f"URL: {url}")
            return False
        total_length = response.headers.get('content-length')
        progress = cli.progress_bar(f"Downloading {self.name} from {self.server}", vanish=True)

        with open(SOURCES_DIR + "/" + self.file + ".tmp", "wb") as temporary_file:
            if total_length is None:
                try:
                    temporary_file.write(response.content)
                except Exception as e:
                    progress.fail("Error while writing to disk: ")
                    print(e)
                    report(self.severity, "download - " + self.name, "Could not write to disk!",
                           software=self.name, exception=e)
                    return False
            else:
                try:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=load("data/config.json", default=CONFIG).json["batch_size"]):
                        dl = dl + len(data)  # Should be 1024
                        temporary_file.write(data)
                        done = 100 - int(((total_length - dl) / total_length) * 100)  # 100 - (remaining / total)*100
                        progress.update(done)
                except Exception as e:
                    progress.fail("Error while writing chunk to disk: ")
                    print(e)
                    report(self.severity, "download - " + self.name, "Could not write chunk to disk!",
                           software=self.name, exception=e)
                    try:
                        remove(SOURCES_DIR + "/" + self.file + ".tmp")
                    except Exception as e:
                        cli.fail("Error while removing temporary file: (NON-FATAL)")
                        print(e)
                        report(int(self.severity / 2), f"download - clean up failure {self.name}",
                               "Could not delete temporary download file!",
                               additional="Not deleted: " + self.file + ".tmp", exception=e, software=self.name)

                    return False

        if "tasks" in self.config and enabled(self.config["tasks"]):
            context.task = "executing after update tasks"
            # Generate temporary directory
            progress.update_message("Initializing tasks")
            tmp_dir = abs_filename(SOURCES_DIR + "/task-" + self.name.replace(" ", "_") + "-build" + str(self.replaceable["%build%"]))
            # very well-designed very well hahah

            def clean_up():
                """
                Try deleting all temporary things
                :return:
                """
                if self.config["tasks"]["cleanup"]:
                    try:
                        remove(SOURCES_DIR + "/" + self.file + ".tmp")
                    except Exception as e_cup:
                        cli.fail(f"Error while removing temporary downloaded file: {e_cup}")
                        report(int(self.severity / 2), f"download - clean up after task failure {self.name}",
                               "Could not delete temporary downloaded file!",
                               additional=f"Not deleted: {self.file}.tmp", exception=e, software=self.name)
                    try:
                        rmtree(tmp_dir)
                    except Exception as e_cup:
                        cli.fail(f"Error while removing temporary task directory after failure: {e_cup}")
                        report(int(self.severity / 2),
                               f"download - clean up temporary directory after task failure ({self.name})",
                               "Could not delete temporary directory!", additional=f"Not deleted: {tmp_dir}",
                               exception=e, software=self.name)

            try:
                makedirs(tmp_dir, exist_ok=True)
            except Exception as e:
                cli.fail(f"Could not initialize temporary task directory for {self.name}: {e}")
                report(self.severity, "download - create temporary task directory " + self.name,
                       "Could not create directory", software=self.name, exception=e)
                if self.config["tasks"]["cleanup"]:
                    try:
                        remove(SOURCES_DIR + "/" + self.file + ".tmp")
                    except Exception as e:
                        cli.fail(f"Error while removing temporary downloaded file for {self.name}: {e}")
                        report(int(self.severity / 2), "download - clean up after task failure" + self.name,
                               "Could not delete temporary downloaded file!",
                               additional="Not deleted: " + self.file + ".tmp", exception=e, software=self.name)
                return False  # Not updated.

            if self.config["tasks"]["copy_downloaded"]:
                progress.update_message("Initializing temporary directory, copying files")
                try:
                    copy(SOURCES_DIR + "/" + self.file + ".tmp", tmp_dir + "/" + self.file)
                except Exception as e:
                    progress.fail(f"Error while copying temporary file to temporary folder for {self.name}: {e}")
                    report(self.severity, "copy - " + self.name,
                           "Could not copy downloaded files into temporary task directory!",
                           software=self.name, exception=e)
                    clean_up()
                    return False  # Not updated.

                # Done with all temporary directory setup

                for task in self.config["tasks"]["tasks"]:
                    if enabled(task):
                        progress.update_message(task["progress"]["message"], done=task["progress"]["value"])
                        if not execute(task, tmp_dir, self.replaceable, final_dest=f"{SOURCES_DIR}/{self.file}.tmp"):
                            clean_up()
                            return False

                progress.update_message("Tasks complete, cleaning...", done=99)
                try:
                    rmtree(tmp_dir)
                except Exception as e:
                    cli.fail("Error while removing temporary: (NOT-FATAL)")
                    print(e)
                    report(int(self.severity / 2),
                           "tasks - clean up temporary directory after task completed" + self.name,
                           "Could not delete temporary directory! (NON FATAL)", additional="Not deleted: " + tmp_dir,
                           exception=e, software=self.name)

        progress.update_message("Cleaning up...")
        progress.update(5)
        try:
            copy(SOURCES_DIR + "/" + self.file + ".tmp", SOURCES_DIR + "/" + self.file)
        except Exception as e:
            progress.fail(f"Error while copying downloaded .tmp file for {self.name}: {e}")
            report(self.severity, "copy - " + self.name, "Could not copy downloaded files!",
                   software=self.name, exception=e)
            return False
        progress.update(50)
        try:
            remove(SOURCES_DIR + "/" + self.file + ".tmp")
        except Exception as e:
            progress.fail(f"Error while removing downloaded file for {self.name}: {e}")
            report(int(self.severity / 2), "download - " + self.name, "Could not delete temporary files!",
                   additional="Not deleted: " + self.file + ".tmp", exception=e, software=self.name)
            return True

        progress.complete("Updated " + self.name)
        return True

    def update(self, check: bool, force_retrieve: bool) -> bool:
        """
        Try to find updates for this source and update if necessary
        :param check: Weather to force check compatibility changes
        :param force_retrieve: Weather to force download the software
        :return: Weather or not the update was successful
        """
        if "compatibility" in self.config and enabled(self.config["compatibility"]) and \
                (self.config["compatibility"]["check"] == "always" or check):
            self.check_compatibility()
        newest_build = self.get_newest_build()
        cli.info(f"Newest build for {self.name} is {newest_build}", vanish=True)
        if newest_build != self.config["build"]["local"] or force_retrieve:
            self.replaceable["%build%"] = newest_build
            if "compatibility" in self.config and enabled(self.config["compatibility"]) and \
                    self.config["compatibility"]["check"] == "build" and not check:
                self.check_compatibility()
            if self.download_build():
                self.config["build"]["local"] = newest_build
                cli.success(f"Downloaded build {newest_build} for {self.name}!")
                return True
        return False
