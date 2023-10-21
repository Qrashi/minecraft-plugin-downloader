"""
Software management tools
"""
from os import stat

from utils.file_defaults import CONFIG
import utils.cli as cli
from .dict_utils import enabled
from .errors import report
from singlejson import load
from .io import generate
from .sha244 import get_hash
from .source import Source

from shutil import copy
from .versions import VersionRangeRequirement
from .context_manager import context


class Software:
    """
    Software to use in servers (can also be configuration), in genereal a managed file
    """

    def __init__(self, software, name):
        """
        Initialize the software and load parameters
        :param software: Software data
        :param name: name of software
        """
        context.name = name
        self.name = name
        if self.has_source():
            self.source = Source(name)

        self.identifier = software["identifier"]
        self.severity = software["severity"]
        self.requirements = VersionRangeRequirement(software["requirements"])
        self.hash = software["hash"]
        self.file = load("data/config.json", default=CONFIG).json["sources_folder"] + "/" + software["file"]

    def has_source(self) -> bool:
        """
        Check if software has source (way to retrieve the newest builds)
        :return: boolean (has or does not have)
        """
        sources = load("data/sources.json", default="{}").json
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

    def retrieve_newest(self, check: bool, force_retrieve: bool, software_data) -> bool:
        """
        Retrieves the newest version from the internet if possible
        :param check: bool; Always fetch compatibility
        :param force_retrieve: bool; Always download the newest build
        :param software_data: The config data corresponding to the software
        :return bool: Dependency was updated in some way
        """
        context.failure_severity = self.severity
        context.name = self.name
        if self.has_source():
            updated = self.source.update(check, force_retrieve)
            self.hash = self.get_hash()
            self.requirements = VersionRangeRequirement(software_data["requirements"])
            return updated
        new_hash = self.get_hash()
        if new_hash != self.hash:
            cli.success("Detected update for " + self.name)
            self.hash = new_hash
            return True
        self.hash = new_hash
        return False

    def copy(self, server: str) -> bool:
        """
        Copies dependency into the server if possible.
        :param server: Name of the server
        :return bool: If the server was updated
        """
        context.failure_severity = self.severity
        context.name = self.name
        context.task = f"copying to server \"{server}\""
        servers = load("data/servers.json", default="{}").json
        server_info = servers[server]
        destination_path = server_info["path"] + server_info["software"][self.name]["copy_path"]
        # Generate destination file...
        try:
            generate(destination_path, default="")
        except Exception as e:
            report(self.severity, f"copy - {self.name} > {server}", f"Could not generate destination file at " +
                   f"{destination_path}! Could be a permission error.",
                   exception=e, software=self.name)
            cli.fail(f"Could not copy {self.name} to {server}!")
            return False

        # Copy file
        try:
            copy(self.file, destination_path)
        except Exception as e:
            report(self.severity, f"copy - {self.name} > {server}", "Copy process did not finish: ",
                   exception=e, software=self.name)
            cli.fail(f"Could not copy {self.name} to {server} - see errors.json!")
            return False
        return True


if __name__ == "__main__":
    print("blas mir die huf auf")
