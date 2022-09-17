"""
Software management tools
"""
from os import stat

from utils.file_defaults import CONFIG
import utils.cli as cli
from .dict_utils import enabled
from .errors import report
from singlejson import pool
from .io import generate
from .sha244 import get_hash
from .source import Source
import sys
from .versions import VersionRangeRequirement
from .context_manager import context


class Software:
    """
    Software to use in servers (can also be configuration), in genereal a managed file
    """

    def __init__(self, software):
        """
        Initialize the software and load parameters
        :param software: Software to load (name of software)
        """
        software_json = pool.open("data/software.json", default="{}").json
        if software not in software_json:
            report(9, "software class", "Typo in config: Could not find specified software, exiting!",
                   additional="Provided software: " + software)
            sys.exit()
        self.name = software
        if self.has_source():
            self.source = Source(software)

        self.identifier = software_json[software]["identifier"]
        self.severity = software_json[software]["severity"]
        self.requirements = VersionRangeRequirement(software_json[software]["requirements"])
        self.hash = software_json[software]["hash"]
        self.file = pool.open("data/config.json", default=CONFIG).json["sources_folder"] + "/" + software_json[software]["file"]

    def has_source(self) -> bool:
        """
        Check if software has source (way to retrieve the newest builds)
        :return: boolean (has or does not have)
        """
        sources = pool.open("data/sources.json", default="{}").json
        if self.name in sources:
            return enabled(sources[self.name])
        return False

    def get_hash(self):
        """
        Retrieve hash for local file
        :return:
        """
        return get_hash(self.file)

    def needs_update(self, other: str) -> bool:
        """
        Checks if the remote file hash is equal to the current hash
        :return bool: If there has been a file change
        """
        return self.hash != get_hash(other)

    def retrieve_newest(self, check: bool, force_retrieve: bool) -> bool:
        """
        Retrieves the newest version from the internet if possible
        :param force_retrieve: bool; Always download the newest build
        :param check: bool; Always fetch compatibility
        :return bool: Dependency was updated in some way
        """
        context.failure_severity = self.severity
        context.name = self.name
        if self.has_source():
            updated = self.source.update(check, force_retrieve)
            self.hash = self.get_hash()
            return updated
        new_hash = self.get_hash()
        if new_hash != self.hash:
            cli.success("Detected update for " + self.name)
            self.hash = new_hash
            return True
        self.hash = new_hash
        return False

    def copy(self, server: str, dependency_number: str) -> bool:
        """
        Copies dependency into the server if possible.
        :param server: Name of the server
        :param dependency_number: The "x/y" to display at the end of the progress bar
        :return bool: If the server was updated
        """
        context.failure_severity = self.severity
        context.name = self.name
        context.task = f"copying to server \"{server}\""
        servers = pool.open("data/servers.json", default="{}").json
        server_info = servers[server]
        destination_path = server_info["path"] + server_info["software"][self.name]["copy_path"]
        progress = cli.progress_bar(f"Updating {self.name} in {server} {dependency_number}", vanish=True)
        # Generate destination file...
        try:
            generate(destination_path, default="")
        except Exception as e:
            report(self.severity, "copy - " + self.name + " > " + server,
                   "Could not generate destination file at " + self.file + "! Could be a permission error.",
                   exception=e, software=self.name)
            progress.fail("Could not copy " + self.name + " to " + server + ": ")
            print(e)
            cli.warn("Skipping copy...")
            return False

        # Copy file
        try:
            with open(self.file, "rb") as source, open(destination_path, "wb") as destination:
                copied = 0  # Copied bytes
                total = stat(self.file).st_size
                while True:
                    piece = source.read(pool.open("data/config.json", default=CONFIG).json["batch_size"])
                    if not piece:
                        break  # End of file
                    copied += len(piece)
                    destination.write(piece)
                    progress.update((copied / total * 100))
                progress.complete(f"Updated {self.name} in {server}! {dependency_number}")
        except Exception as e:
            report(self.severity, "copy - " + self.name + " > " + server, "Copy process did not finish: ",
                   exception=e, software=self.name)
            progress.fail("Update failed: ")
            print(e)
            cli.warn("Skipping copy")
            return False
        return True


if __name__ == "__main__":
    print("blas mir die huf auf")
