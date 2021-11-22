import datetime
from os import remove, makedirs
from shutil import copy, rmtree

from requests import get

from .URLAccessField import URLAccessField
from .cli_provider import cli
from .error import report
from .events import report as report_event
from .file_pool import pool
from .version import Version, is_valid, VersionRangeRequirement
from .task_executor import execute
from .files import abs_filename

FOLDER = pool.open("data/config.json").json["sources_folder"]


def check_enabled(json: dict) -> bool:
    if "enabled" in json:
        return json["enabled"]
    return True

# TODO: Use check enabled in almost all cases


class Source:
    def __init__(self, source: str):
        sources = pool.open("data/sources.json").json
        if source not in sources:
            report("source class", 9, "Typo in config: Could not find specified source, terminating!",
                   additional="Provided source: " + source)
            exit()

        source_info = sources[source]
        self.source = source
        self.server = source_info["server"]
        self.last_check = source_info["last_checked"]
        self.config: dict = source_info
        all_software = pool.open("data/software.json").json

        self.severity = all_software[source]["severity"]
        self.file = all_software[source]["file"]

        def generate_replace(version_to_use: Version):
            def replace(string: str) -> str:
                replaced = string.replace("%newest_version%", version_to_use.string())
                replaced = replaced.replace("%newest_major%", "1." + str(version_to_use.major))
                replaced = replaced.replace("%newest_minor%", "." + str(version_to_use.minor))
                return replaced

            return replace

        if "compatibility" in source_info:
            access = URLAccessField(self.config["compatibility"]["remote"])
            try:
                response = get(access.url)  # Replace all placeholders in the string and then
            except Exception as e:  # Error while fetching
                report("version check -" + source, self.severity,
                       "Could not fetch latest version information!",
                       additional="Last update: " + self.last_check, exception=e)
                cli.fail("Could not retrieve newest version for " + self.source + ":")
                print(e)
                self.newest_replacer = generate_replace(Version(pool.open("data/versions.json").json["current_version"]))
                return

            if response.status_code != 200:  # Server side error
                report("download -" + source, self.severity,
                       "Error while fetching latest build information: Status code " + str(response.status_code),
                       additional="Last update: " + self.last_check)
                cli.fail("Could not retrieve newest version for " + self.source + " - status code " + str(
                    response.status_code))
                self.newest_replacer = generate_replace(Version(pool.open("data/versions.json").json["current_version"]))
                return

            field = access.access(response.json())
            if type(field) == str:
                newest = Version(field)
                if source_info["compatibility"]["behaviour"].endswith("max"):
                    compatibility = VersionRangeRequirement((newest, Version((newest.major, "99"))))
                else:
                    compatibility = VersionRangeRequirement((newest, newest))
            elif type(field) == list:
                if len(field) == 0:
                    report("Compatibility checker", self.severity, self.source + " has NO compatibilities (list is empty) (" + str(field) + ")", additional=self.last_check)
                    cli.fail("Could not fetch compatibility for " + self.source + " - no compatibilities found!")
                    self.newest_replacer = generate_replace(Version(pool.open("data/versions.json").json["current_version"]))

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
                if source_info["compatibility"]["behaviour"].endswith("|max"):
                    maxed_newest = Version((newest.major, "99"))
                if source_info["compatibility"]["behaviour"].startswith("max|"):
                    compatibility = VersionRangeRequirement((lowest, maxed_newest))
                else:
                    compatibility = VersionRangeRequirement((newest, maxed_newest))
            else:
                report("Compatibility checker", self.severity, "Compatibility is not of type array or string! type: " + str(field), additional=self.last_check)
                cli.fail("Could not fetch compatibility for " + self.source + " - no list of compatibilities or compatibility found!")
                self.newest_replacer = generate_replace(Version(pool.open("data/versions.json").json["current_version"]))
                return

            previous_compatibility = VersionRangeRequirement(all_software[self.source]["requirements"])
            if not previous_compatibility.matches(compatibility):
                all_software[self.source]["requirements"] = compatibility.dict()
                cli.success("Detected version increment for " + source + "!")
                report_event("Compatibility checker", "Compatibility for " + source + " has been changed to " + compatibility.string() + "!")

            self.newest_replacer = generate_replace(newest)

        else:
            # Just use newest game version
            newest_version = Version(pool.open("data/versions.json").json["current_version"])
            self.newest_replacer = generate_replace(Version(pool.open("data/versions.json").json["current_version"]))

    def get_newest_build(self) -> int:
        url_field = URLAccessField(self.config["build"]["remote"])
        try:
            response = get(self.newest_replacer(url_field.url))  # Replace all placeholders in the string and then
        except Exception as e:  # Error while fetching
            report("fetching build information -" + self.source, self.severity,
                   "Could not fetch latest build information!",
                   additional="Last update: " + self.last_check, exception=e)
            cli.fail("Could not fetch latest build information: ")
            print(e)
            cli.warn("Skipping...")
            return self.config["build"]["local"]

        if response.status_code != 200:  # Server side error or typo
            report("fetching build information -" + self.source, self.severity,
                   "Error while fetching latest build information: Status code " + str(response.status_code),
                   additional="Last update: " + self.last_check)
            cli.fail("Could not fetch latest build information - status code " + str(response.status_code))
            cli.warn("Skipping...")
            return self.config["build"]["local"]

        field = url_field.access(response.json())

        def _int(string_to_int, throw_error=False) -> int:
            if type(string_to_int) == int:
                return int(string_to_int)
            if string_to_int.isdigit():
                return int(string_to_int)
            elif throw_error:
                report("fetching builds - " + self.source, self.severity, "Expected field of type str, got " + str(string_to_int), additional=self.last_check)
                cli.fail("Could not fetch latest build information, expected string, got " + str(string_to_int))
                return self.config["build"]["local"]
                # Wont download newer version if the newer build is the local build
            else:
                return self.config["build"]["local"]
                # Wont download newer version if the max build is the local build

        if type(field) == str or type(field) == int:
            pool.open("data/sources.json").json[self.source]["last_checked"] = datetime.datetime.now().strftime(
                "%m.%d %H:%M")
            return _int(field, throw_error=True)
        elif type(field) == list:
            # List of builds
            if len(field) == 0:
                # No builds!
                cli.fail("Could not fetch latest build for " + self.source + ", there are no builds (list of builds is empty)")
                report("download - " + self.source, self.severity, "List of builds is EMPTY (" + str(field), additional=self.last_check)
            if len(field) == 1:
                return _int(field[0], throw_error=True)
            builds = []
            for build in field:
                builds.append(_int(build))
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
                response = get((self.newest_replacer(access.url)).replace("%build%", str(build)))
            except Exception as e:
                cli.fail("Could not fetch artifact name for build " + str(build) + " of " + self.source + " error while initiating connection")
                report("download - " + self.source, self.severity, "Exception while fetching artifact name!", additional="Last update: " + self.last_check, exception=e)
                return False
            if response.status_code != 200:
                cli.fail("Could not fetch artifact name for build " + str(build) + " of " + self.source + " status code " + str(response.status_code))
                report("download - " + self.source, self.severity, "Exception while fetching artifact name - code " + str(response.status_code),
                       additional="Last update: " + self.last_check)
                return False
            try:
                artifact = access.access(response.json())
            except Exception as e:
                cli.fail("Error while retrieving artifact name for build " + str(build) + " of " + self.source + "!")
                report("download - " + self.source, self.severity,
                       "Exception while accessing json!",
                       additional="Last update: " + self.last_check, exception=e)
                return False
        else:
            artifact = ""

        try:
            response = get(((self.newest_replacer(self.config["build"]["download"])).replace("%build%", str(build))).replace("%artifact%", artifact),
                           stream=True)
        except Exception as e:
            cli.fail("Could not start download of " + self.source + " - aborting")
            report("download - " + self.source, self.severity, "Exception while downloading!",
                   additional="Last update: " + self.last_check, exception=e)
            return Falseremove
        if response.status_code != 200:
            cli.fail(
                "Failure while downloading " + self.source + " from " + self.server + " - status code " + str(
                    response.status_code) + " - aborting download")
            report("download - " + self.source, self.severity,
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
                    report("download - " + self.source, self.severity, "Could not write to disk!",
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
                    report("download - " + self.source, self.severity, "Could not write chunk to disk!",
                           additional="Last update: " + self.last_check, exception=e)
                    try:
                        remove(FOLDER + "/" + self.file + ".tmp")
                    except Exception as e:
                        cli.fail("Error while removing temporary file: (NOT-FATAL)")
                        print(e)
                        report("download - clean up failure " + self.source, int(self.severity / 2), "Could not delete temporary download file!",
                               additional="Not deleted: " + self.file + ".tmp", exception=e)

                    return False

        if "tasks" in self.config:
            if check_enabled(self.config["tasks"]):
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
                            report("download - clean up after task failure" + self.source, int(self.severity / 2),
                                   "Could not delete temporary downloaded file!",
                                   additional="Not deleted: " + self.file + ".tmp", exception=e)
                        try:
                            rmtree(tmp_dir)
                        except Exception as e:
                            cli.fail("Error while removing temporary task directory after failure: (NOT-FATAL)")
                            print(e)
                            report("download - clean up temporary directory after task failure" + self.source, int(self.severity / 2),
                                   "Could not delete temporary directory!",
                                   additional="Not deleted: " + tmp_dir, exception=e)

                try:
                    makedirs(tmp_dir, exist_ok=True)
                except Exception as e:
                    cli.fail("Could not initialize temporary task directory!")
                    print(e)
                    report("download - create temporary task directory " + self.source, self.severity, "Could not create directory", additional="Last update: " + self.last_check, exception=e)
                    if self.config["tasks"]["cleanup"]:
                        try:
                            remove(FOLDER + "/" + self.file + ".tmp")
                        except Exception as e:
                            cli.fail("Error while removing temporary downloaded file: (NOT-FATAL)")
                            print(e)
                            report("download - clean up after task failure" + self.source, int(self.severity / 2),
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
                        report("copy - " + self.source, self.severity, "Could not copy downloaded files into temporary task directory!",
                               additional="Last update: " + self.last_check, exception=e)
                        handle_error()
                        return False  # Not updated.

                # Done with all temporary directory setup

                def replace(string: str) -> str:
                    return self.newest_replacer(string.replace("%build%", str(build)))

                for task in self.config["tasks"]["tasks"]:
                    progress.update_message(task["progress"]["message"], done=task["progress"]["value"])
                    if not execute(task, tmp_dir, replace, FOLDER + "/" + self.file + ".tmp", self.source, self.last_check, self.severity):
                        handle_error()
                        return False

                progress.update_message("Tasks complete, cleaning...", done=99)
                try:
                    rmtree(tmp_dir)
                except Exception as e:
                    cli.fail("Error while removing temporary: (NOT-FATAL)")
                    print(e)
                    report("tasks - clean up temporary directory after task completed" + self.source,
                           int(self.severity / 2),
                           "Could not delete temporary directory! (NON FATAL)",
                           additional="Not deleted: " + tmp_dir, exception=e)

        progress.update_message("Cleaning up...")
        progress.update(5)
        try:
            copy(FOLDER + "/" + self.file + ".tmp", FOLDER + "/" + self.file)
        except Exception as e:
            progress.fail("Error while copying downloaded file: ")
            print(e)
            report("copy - " + self.source, self.severity, "Could not copy downloaded files!",
                   additional="Last update: " + self.last_check, exception=e)
            return False
        progress.update(50)
        try:
            remove(FOLDER + "/" + self.file + ".tmp")
        except Exception as e:
            progress.fail("Error while removing downloaded file: (NOT-FATAL)")
            print(e)
            report("download - " + self.source, int(self.severity / 2), "Could not delete temporary files!",
                   additional="Not deleted: " + self.file + ".tmp", exception=e)
            return True

        progress.complete("Updated " + self.source)
        return True

    def update(self):
        newest_build = self.get_newest_build()
        if newest_build > self.config["build"]["local"]:
            if self.download_build(newest_build):
                pool.open("data/sources.json").json[self.source]["build"]["local"] = newest_build
