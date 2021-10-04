import datetime
from os import remove
from shutil import copy

from requests import get

from .URLAccessField import URLAccessField
from .cli_provider import cli
from .error import report
from .events import report as report_event
from .file_pool import pool
from .version import Version, is_valid

FOLDER = pool.open("data/config.json").json["sources_folder"]


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
        self.config = source_info
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

        if "newest" in source_info:
            if is_valid(source_info["newest"]):
                newest_version = Version(source_info["newest"])
                self.version = newest_version
                self.newest_replacer = generate_replace(self.version)
            else:
                url_access_field = URLAccessField(self.config["newest"])
                try:
                    response = get(url_access_field.url)  # Replace all placeholders in the string and then
                except Exception as e:  # Error while fetching
                    report("version check -" + source, self.severity,
                           "Could not fetch latest version information!",
                           additional="Last update: " + self.last_check, exception=e)
                    cli.fail("Could not retrieve newest version for " + self.source + ":")
                    print(e)
                    self.version = Version(pool.open("data/versions.json").json["current_version"])
                    self.newest_replacer = generate_replace(self.version)
                    return

                if response.status_code != 200:  # Server side error
                    report("download -" + source, self.severity,
                           "Error while fetching latest build information: Status code " + str(response.status_code),
                           additional="Last update: " + self.last_check)
                    cli.fail("Could not retrieve newest version for " + self.source + " - status code " + str(
                        response.status_code))
                    self.version = Version(pool.open("data/versions.json").json["current_version"])
                    self.newest_replacer = generate_replace(self.version)
                    return

                field = url_access_field.access(response.json())
                if type(field) == str:
                    newest = Version(field)
                else:
                    newest = Version("1.0")
                    for version in field:
                        version_obj = Version(version)
                        if newest.is_lower(version_obj):
                            newest = version_obj

                if "previous_version" in source_info:
                    if not Version(source_info["previous_version"]).matches(
                            newest):  # Dependency version increment detected
                        report_event("Source class", "Version increment for " + source + " detected!")
                        software_file = pool.open("data/software.json")
                        software_file.json[source]["version"] = newest.string()
                else:
                    sources[source]["previous_version"] = newest.string()
                self.version = newest
                self.newest_replacer = generate_replace(self.version)

        else:
            # Just use newest game version
            newest_version = Version(pool.open("data/versions.json").json["current_version"])
            self.version = newest_version
            self.newest_replacer = generate_replace(self.version)

    def get_newest_build(self):
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
        if type(field) == str:
            pool.open("data/sources.json").json[self.source]["last_checked"] = datetime.datetime.now().strftime(
                "%m.%d %H:%M")
            return field  # Response is just newest version string
        else:
            current = self.config["build"]["local"]
            for build in field:
                if type(build) == str:
                    if build.isdigit():
                        build = int(build)
                    else:
                        report("fetching newest build data", 1,
                               "Could not convert build ID " + build + " to comparable string!",
                               additional="Source: " + self.source)
                        build = current
                if current < build:
                    current = build  #
            pool.open("data/sources.json").json[self.source]["last_checked"] = datetime.datetime.now().strftime(
                "%m.%d %H:%M")
            return current

    def download_build(self, build: int) -> bool:
        """

        :param build: success
        :return:
        """
        try:
            response = get((self.newest_replacer(self.config["build"]["download"])).replace("%build%", str(build)),
                           stream=True)
        except Exception as e:
            cli.fail("Could not start download of " + self.source + " - aborting")
            report("download - " + self.source, self.severity, "Exception while downloading!",
                   additional="Last update: " + self.last_check, exception=e)
            return False
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
                progress.complete("Downloaded " + self.source)
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
                    return False
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
        progress.complete("Downloaded " + self.source)
        return True

    def update(self):
        newest_build = self.get_newest_build()
        if newest_build != self.config["build"]["local"]:
            if self.download_build(newest_build):
                pool.open("data/sources.json").json[self.source]["build"]["local"] = newest_build
