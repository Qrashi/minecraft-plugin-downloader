from os import stat

from utils.FileAccessField import FileAccessField
from .cli_provider import cli
from .error import report
from .file_pool import pool
from .files import generate
from .sha244utils import getHash
from .source import Source
from .version import VersionRangeRequirement, Version


class Software:
    def has_source(self) -> bool:
        sources = pool.open("data/sources.json").json
        return self.software in sources

    def __init__(self, software):
        software_json = pool.open("data/software.json").json
        if software not in software_json:
            report("software class", 9, "Typo in config: Could not find specified software, exiting!",
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

    def get_hash(self) -> str:
        """
        Gets hash for file
        :return: hash
        """
        return getHash(self.file)

    def needs_update(self) -> bool:
        """
        If there has been a file change since the last check
        :return bool: If there has been a file change
        """
        return getHash(self.file) != self.hash

    def retrieve_newest(self):
        """
        Retrieves newest version from the internet if possible
        :return:
        """
        cli.info("Retrieving newest version for " + self.software, vanish=True)
        if self.has_source():
            self.source.update()

    def copy(self, server: str) -> bool:
        """
        Copies dependency into the server if possible.
        :param server: Name of the server
        :return bool: If the server was updated
        """
        servers = pool.open("data/servers.json").json
        server_info = servers[server]
        if server_info["version"]["type"] == "version":
            server_version = Version(server_info["version"]["value"])
        else:
            access = FileAccessField(server_info["version"]["value"])
            server_version = Version(access.access(pool.open(access.filepath).json))
        destination_path = server_info["path"] + server_info["software"][self.software]["copy_path"]

        if server_version.fulfills(self.requirements):
            progress = cli.progress_bar("Updating " + self.software + " in " + server, vanish=True)

            # Generate destination file...
            try:
                generate(destination_path, default="")
            except Exception as e:
                report("copy - " + self.software + " > " + server, self.severity,
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
                report("copy - " + self.software + " > " + server, self.severity,
                       "Copy process did not finish: ", exception=e)
                progress.fail("Update failed: ")
                print(e)
                cli.warn("Skipping copy")
                return False
            return True


if __name__ == "__main__":
    print("blas mir die huf auf")
