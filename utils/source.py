import datetime
from os import remove, makedirs
from shutil import copy, rmtree
import sys
from typing import Union

from requests import get

from .URLAccessField import URLAccessField
from .cli_provider import cli
from .dict_utils import enabled
from .errors import report
from .events import report as report_event
from .files import pool
from .io import abs_filename
from .tasks import execute
from .versions import Version, VersionRangeRequirement
from .web_cache import get_cached

FOLDER = pool.open("data/config.json").json["sources_folder"]


class Source:
    def __init__(self, source: str):
        sources = pool.open("data/sources.json").json
        if source not in sources:
            report(9, "source class", "Typo in config: Could not find specified source, terminating!",
                   additional="Provided source: " + source)
            sys.exit()

        source_info = sources[source]
        self.source = source
        if "headers" in source_info:
            self.headers = source_info["headers"]
        else:
            self.headers = pool.open("data/config.json").json["default_header"]
        if "cache_results" in source_info:
            self.caching = source_info["cache_results"]
        else:
            self.caching = True
        self.server = source_info["server"]
        self.last_check = source_info["last_checked"]
        self.config: dict = source_info
        all_software = pool.open("data/software.json").json

        self.severity = all_software[source]["severity"]
        self.file = all_software[source]["file"]

        requirement = VersionRangeRequirement(all_software[self.source]["requirements"])
        version_to_use = requirement.maximum

        def replace(string: str) -> str:
            replaced = string.replace("%newest_version%", version_to_use.string())
            replaced = replaced.replace("%newest_major%", "1." + str(version_to_use.major))
            replaced = replaced.replace("%newest_minor%", "." + str(version_to_use.minor))
            return replaced

        self.newest_replacer = replace

    def check_compatibility(self) -> bool:
        if "compatibility" in self.config:
            if enabled(self.config["compatibility"]):
                access = URLAccessField(self.config["compatibility"]["remote"])
                try:
                    response = get_cached(access.url, self.headers,
                                          self.caching)  # Replace all placeholders in the string and then
                except Exception as e:  # Error while fetching
                    report(self.severity, "version check -" + self.source,
                           "Could not fetch latest version information!",
                           additional="Last update: " + self.last_check, exception=e)
                    cli.fail("Could not retrieve newest version for " + self.source + ":")
                    print(e)
                    return False

                if response.status_code != 200:  # Server side error
                    report(self.severity, "download -" + self.source,
                           "Error while fetching latest build information: Status code " + str(response.status_code),
                           additional="Last update: " + self.last_check)
                    cli.fail("Could not retrieve newest version for " + self.source + " - status code " + str(
                        response.status_code))
                    return False

                all_software = pool.open("data/software.json").json
                previous_compatibility = VersionRangeRequirement(all_software[self.source]["requirements"])

                field = access.access(response.json())
                if type(field) is str:
                    newest = Version(field)
                    lower_newest = Version(field)
                    if self.config["compatibility"]["behaviour"].endswith("|major"):
                        newest = Version((newest.major, "99"))
                        lower_newest = Version((newest.major, ""))
                    if self.config["compatibility"]["behaviour"].startswith("extend|"):
                        compatibility = VersionRangeRequirement((previous_compatibility.minimum, newest))
                    else:  # precise mode
                        compatibility = VersionRangeRequirement((lower_newest, newest))
                elif type(field) is list:
                    if len(field) == 0:
                        report(self.severity, "Compatibility checker",
                               self.source + " has NO compatibilities (list is empty) (" + str(field) + ")",
                               additional=self.last_check)
                        cli.fail("Could not fetch compatibility for " + self.source + " - no compatibilities found!")

                    # Retrieve newest and oldest version
                    newest = Version("1.0")
                    for version in field:
                        version_obj = Version(version)
                        if version_obj.is_higher(newest):
                            newest = version_obj
                    # Retrieve lowest
                    lowest = newest
                    for version in field:
                        version_obj = Version(version)
                        if version_obj.is_lower(lowest):
                            lowest = version_obj
                    maxed_newest = newest
                    if self.config["compatibility"]["behaviour"].endswith("|major"):
                        maxed_newest = Version((newest.major, "99"))
                    if self.config["compatibility"]["behaviour"].startswith("max|"):
                        if self.config["compatibility"]["behaviour"].endswith("|major"):  # all of the max major
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
                           "Compatibility is not of type array or string! type: " + str(field),
                           additional=self.last_check)
                    cli.fail(
                        "Could not fetch compatibility for " + self.source + " - no list of compatibilities or compatibility found!")
                    return False

                if not previous_compatibility.matches(compatibility):
                    all_software[self.source]["requirements"] = compatibility.dict()
                    cli.success("Detected version compatibility increment for " + self.source + "!")
                    report_event("Compatibility checker",
                                 "Compatibility for " + self.source + " has been changed to " + compatibility.string() + "!")

                def replace(string: str) -> str:
                    replaced = string.replace("%newest_version%", newest.string())
                    replaced = replaced.replace("%newest_major%", "1." + str(newest.major))
                    replaced = replaced.replace("%newest_minor%", "." + str(newest.minor))
                    return replaced

                self.newest_replacer = replace
                return True
            # Use previous compatiblility
            return True

    def get_newest_build(self) -> Union[int, str]:
        url_field = URLAccessField(self.config["build"]["remote"])
        try:
            response = get_cached(self.newest_replacer(url_field.url), self.headers,
                                  self.caching)  # Replace all placeholders in the string and then
        except Exception as e:  # Error while fetching
            report(self.severity, f"fetching build information - {self.source}",
                   "Could not fetch latest build information!", additional=f"Last update: {self.last_check}",
                   exception=e)
            cli.fail("Could not fetch latest build information: ")
            print(e)
            cli.warn("Skipping...")
            return self.config["build"]["local"]

        if response.status_code != 200:  # Server side error or typo
            report(self.severity, f"fetching build information - {self.source}",
                   f"Error while fetching latest build information: Status code {response.status_code}",
                   additional=f"Last update: {self.last_check}")
            cli.fail(f"Could not fetch latest build information - status code {response.status_code}")
            cli.warn("Skipping...")
            return self.config["build"]["local"]

        field = url_field.access(response.json())

        def _int(string_to_int, throw_error=False) -> int:
            if type(string_to_int) is int:
                return int(string_to_int)
            if string_to_int.isdigit():
                return int(string_to_int)
            if throw_error:
                report(self.severity, "fetching builds - " + self.source,
                       "Expected field of type str, got " + str(string_to_int), additional=self.last_check)
                cli.fail("Could not fetch latest build information, expected string, got " + str(string_to_int))
                return self.config["build"]["local"]
                # Wont download newer version if the newer build is the local build
            return self.config["build"]["local"]

        if type(field) is str or type(field) is int:
            pool.open("data/sources.json").json[self.source]["last_checked"] = datetime.datetime.now().strftime(
                "%m.%d %H:%M")
            # Single newest build
            return field
        if type(field) is list:
            # List of builds MUST be ints to compare
            if len(field) == 0:
                # No builds!
                cli.fail(
                    "Could not fetch latest build for " + self.source + ", there are no builds (list of builds is empty)")
                report(self.severity, "download - " + self.source, "List of builds is EMPTY (" + str(field),
                       additional=self.last_check)
            if len(field) == 1:
                pool.open("data/sources.json").json[self.source]["last_checked"] = datetime.datetime.now().strftime(
                    "%m.%d %H:%M")
                return _int(field[0], throw_error=True)
            builds = []
            for build in field:
                builds.append(_int(build))
            pool.open("data/sources.json").json[self.source]["last_checked"] = datetime.datetime.now().strftime(
                "%m.%d %H:%M")
            return max(builds)

    def download_build(self, build: int) -> bool:
        """

        :param build: success
        :return:
        """

        if "name" in self.config["build"]:
            # Fetch of name required before build download
            access = URLAccessField(self.config["build"]["name"])
            try:
                response = get_cached((self.newest_replacer(access.url)).replace("%build%", str(build)), self.headers,
                                      self.caching)
            except Exception as e:
                cli.fail("Could not fetch artifact name for build " + str(
                    build) + " of " + self.source + " error while initiating connection")
                report(self.severity, "download - " + self.source, "Exception while fetching artifact name!",
                       additional="Last update: " + self.last_check, exception=e)
                return False
            if response.status_code != 200:
                cli.fail("Could not fetch artifact name for build " + str(
                    build) + " of " + self.source + " status code " + str(response.status_code))
                report(self.severity, "download - " + self.source,
                       "Exception while fetching artifact name - code " + str(response.status_code),
                       additional="Last update: " + self.last_check)
                return False
            try:
                artifact = access.access(response.json())
            except Exception as e:
                cli.fail("Error while retrieving artifact name for build " + str(build) + " of " + self.source + "!")
                report(self.severity, "download - " + self.source, "Exception while accessing json!",
                       additional="Last update: " + self.last_check, exception=e)
                return False
        else:
            artifact = ""

        try:
            response = get(
                ((self.newest_replacer(self.config["build"]["download"])).replace("%build%", str(build))).replace(
                    "%artifact%", str(artifact)),
                stream=True, allow_redirects=True, headers=self.headers)
        except Exception as e:
            cli.fail("Could not start download of " + self.source + " - aborting")
            report(self.severity, "download - " + self.source, "Exception while downloading!",
                   additional="Last update: " + self.last_check, exception=e)
            return False
        if response.status_code != 200:
            cli.fail(
                "Failure while downloading " + self.source + " from " + self.server + " - status code " + str(
                    response.status_code) + " - aborting download")
            report(self.severity, "download - " + self.source,
                   "Download finished with code " + str(response.status_code),
                   additional="Last update: " + self.last_check)
            return False
        total_length = response.headers.get('content-length')
        progress = cli.progress_bar("Downloading " + self.source + " from " + self.server, vanish=True)

        with open(FOLDER + "/" + self.file + ".tmp", "wb") as temporary_file:
            if total_length is None:
                try:
                    temporary_file.write(response.content)
                except Exception as e:
                    progress.fail("Error while writing to disk: ")
                    print(e)
                    report(self.severity, "download - " + self.source, "Could not write to disk!",
                           additional="Last update: " + self.last_check, exception=e)
                    return False
            else:
                try:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=pool.open("data/config.json").json["batch_size"]):
                        dl = dl + len(data)  # Should be 1024
                        temporary_file.write(data)
                        done = 100 - int(((total_length - dl) / total_length) * 100)  # 100 - (remaining / total)*100
                        progress.update(done)
                except Exception as e:
                    progress.fail("Error while writing chunk to disk: ")
                    print(e)
                    report(self.severity, "download - " + self.source, "Could not write chunk to disk!",
                           additional="Last update: " + self.last_check, exception=e)
                    try:
                        remove(FOLDER + "/" + self.file + ".tmp")
                    except Exception as e:
                        cli.fail("Error while removing temporary file: (NOT-FATAL)")
                        print(e)
                        report(int(self.severity / 2), "download - clean up failure " + self.source,
                               "Could not delete temporary download file!",
                               additional="Not deleted: " + self.file + ".tmp", exception=e)

                    return False
        if "tasks" in self.config and enabled(self.config["tasks"]):
            # Generate temporary directory
            progress.update_message("Initializing tasks")
            tmp_dir = abs_filename(FOLDER + "/task-" + self.source.replace(" ", "_") + "-build" + str(build))

            def handle_error():
                """
                Try deleting all temporary things
                :return:
                """
                if self.config["tasks"]["cleanup"]:
                    try:
                        remove(FOLDER + "/" + self.file + ".tmp")
                    except Exception as e:
                        cli.fail("Error while removing temporary downloaded file: (NOT-FATAL)")
                        print(e)
                        report(int(self.severity / 2), f"download - clean up after task failure {self.source}",
                               "Could not delete temporary downloaded file!",
                               additional=f"Not deleted: {self.file}.tmp", exception=e)
                    try:
                        rmtree(tmp_dir)
                    except Exception as e:
                        cli.fail("Error while removing temporary task directory after failure: (NOT-FATAL)")
                        print(e)
                        report(int(self.severity / 2),
                               f"download - clean up temporary directory after task failure ({self.source})",
                               "Could not delete temporary directory!", additional=f"Not deleted: {tmp_dir}",
                               exception=e)

            try:
                makedirs(tmp_dir, exist_ok=True)
            except Exception as e:
                cli.fail("Could not initialize temporary task directory!")
                print(e)
                report(self.severity, "download - create temporary task directory " + self.source,
                       "Could not create directory", additional="Last update: " + self.last_check, exception=e)
                if self.config["tasks"]["cleanup"]:
                    try:
                        remove(FOLDER + "/" + self.file + ".tmp")
                    except Exception as e:
                        cli.fail("Error while removing temporary downloaded file: (NOT-FATAL)")
                        print(e)
                        report(int(self.severity / 2), "download - clean up after task failure" + self.source,
                               "Could not delete temporary downloaded file!",
                               additional="Not deleted: " + self.file + ".tmp", exception=e)
                return False  # Not updated.

            if self.config["tasks"]["copy_downloaded"]:
                progress.update_message("Initializing temporary directory, copying files")
                try:
                    copy(FOLDER + "/" + self.file + ".tmp", tmp_dir + "/" + self.file)
                except Exception as e:
                    progress.fail("Error while copying temporary file to temporary folder: ")
                    print(e)
                    report(self.severity, "copy - " + self.source,
                           "Could not copy downloaded files into temporary task directory!",
                           additional="Last update: " + self.last_check, exception=e)
                    handle_error()
                    return False  # Not updated.

                # Done with all temporary directory setup

                def replace(string: str) -> str:
                    return self.newest_replacer(string.replace("%build%", str(build)))

                for task in self.config["tasks"]["tasks"]:
                    if enabled(task):
                        progress.update_message(task["progress"]["message"], done=task["progress"]["value"])
                        if not execute(task, tmp_dir, replace, FOLDER + "/" + self.file + ".tmp", self.source,
                                       self.last_check, self.severity):
                            handle_error()
                            return False

                progress.update_message("Tasks complete, cleaning...", done=99)
                try:
                    rmtree(tmp_dir)
                except Exception as e:
                    cli.fail("Error while removing temporary: (NOT-FATAL)")
                    print(e)
                    report(int(self.severity / 2),
                           "tasks - clean up temporary directory after task completed" + self.source,
                           "Could not delete temporary directory! (NON FATAL)", additional="Not deleted: " + tmp_dir,
                           exception=e)

        progress.update_message("Cleaning up...")
        progress.update(5)
        try:
            copy(FOLDER + "/" + self.file + ".tmp", FOLDER + "/" + self.file)
        except Exception as e:
            progress.fail("Error while copying downloaded file: ")
            print(e)
            report(self.severity, "copy - " + self.source, "Could not copy downloaded files!",
                   additional="Last update: " + self.last_check, exception=e)
            return False
        progress.update(50)
        try:
            remove(FOLDER + "/" + self.file + ".tmp")
        except Exception as e:
            progress.fail("Error while removing downloaded file: (NOT-FATAL)")
            print(e)
            report(int(self.severity / 2), "download - " + self.source, "Could not delete temporary files!",
                   additional="Not deleted: " + self.file + ".tmp", exception=e)
            return True

        progress.complete("Updated " + self.source)
        return True

    def update(self, check: bool, force_retrieve: bool) -> bool:
        checked = False
        if check:
            self.check_compatibility()
            checked = True
        if "%newest_" in URLAccessField(self.config["build"][
                                            "remote"]).url and not checked:  # Check if newest build request requires version data, and update if so
            self.check_compatibility()
            checked = True
        newest_build = self.get_newest_build()
        cli.info("Newest build for " + self.source + " is " + str(newest_build), vanish=True)
        if newest_build != self.config["build"]["local"] or force_retrieve:
            if not checked:
                self.check_compatibility()
            if self.download_build(newest_build):
                pool.open("data/sources.json").json[self.source]["build"]["local"] = newest_build
                cli.success("Downloaded build " + str(newest_build) + " for " + self.source + "!")
                return True
        return False
