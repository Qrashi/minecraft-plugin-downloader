from os import stat

from .cli_provider import cli
from .errors import report
from .files import pool
from .io import generate
from .sha244 import get_hash
from .source import Source
from .versions import VersionRangeRequirement
from .dict_utils import enabled


class Software:
    def has_source(self) -> bool:
        sources = pool.open("data/sources.json").json
        if self.software in sources:
            return enabled(sources[self.software])
        return False

    def __init__(self, software):
        software_json = pool.open("data/software.json").json
        if software not in software_json:
            report(9, "software class", "Typo in config: Could not find specified software, exiting!",
                   additional="Provided software: " + software)
            exit()
        self.software = software
        if self.has_source():
            self.source = Source(software)

        self.identifier = software_json[software]["identifier"]
        self.severity = software_json[software]["severity"]
        self.requirements = VersionRangeRequirement(software_json[software]["requirements"])
        self.hash = software_json[software]["hash"]
        self.file = pool.open("data/config.json").json["sources_folder"] + "/" + software_json[software]["file"]

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

    def retrieve_newest(self, check: bool, force_retrieve: bool) -> tuple[bool, str]:
        """
        Retrieves newest version from the internet if possible
        :param force_retrieve: bool; Always download newest build
        :param check: bool; Always fetch compatibility
        :return bool: Dependency was updated in some way
        :return str: The new hash
        """
        cli.info("Retrieving newest version for " + self.software, vanish=True)
        if self.has_source():
            self.source.update(check, force_retrieve)
        old_hash = self.hash
        new_hash = self.get_hash()
        return old_hash == new_hash, new_hash

    def copy(self, server: str) -> bool:
        """
        Copies dependency into the server if possible.
        :param server: Name of the server
        :return bool: If the server was updated
        """
        servers = pool.open("data/servers.json").json
        server_info = servers[server]
        destination_path = server_info["path"] + server_info["software"][self.software]["copy_path"]
        progress = cli.progress_bar("Updating " + self.software + " in " + server, vanish=True)
        # Generate destination file...
        try:
            generate(destination_path, default="")
        except Exception as e:
            report(self.severity, "copy - " + self.software + " > " + server,
                   "Could not generate destination file at " + self.file + "! Could be a permission error.",
                   exception=e)
            progress.fail("Could not copy " + self.software + " to " + server + ": ")
            print(e)
            cli.warn("Skipping copy...")
            return False

        # Copy file
        try:
            with open(self.file, "rb") as source, open(destination_path, "wb") as destination:
                copied = 0  # Copied bytes
                total = stat(self.file).st_size
                while True:
                    piece = source.read(pool.open("data/config.json").json["batch_size"])
                    if not piece:
                        break  # End of file
                    copied += len(piece)
                    destination.write(piece)
                    progress.update((copied / total * 100))
                progress.complete("Updated " + self.software + "!")
        except Exception as e:
            report(self.severity, "copy - " + self.software + " > " + server, "Copy process did not finish: ",
                   exception=e)
            progress.fail("Update failed: ")
            print(e)
            cli.warn("Skipping copy")
            return False
        return True


if __name__ == "__main__":
    print("blas mir die huf auf")
