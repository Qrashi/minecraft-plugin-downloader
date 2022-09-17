"""
The file handling open json (configuration) files
"""
# TODO replace with singlejson
import sys
from typing import Dict

from .cli_provider import cli
from .io import abs_filename
from .json_file import JsonFile

if __name__ == "__main__":
    print("The file pool is only meant to be imported!")
    sys.exit()


class FilePool:
    """
    A FilePool, a collection of files
    """
    def __init__(self):
        """
        Initialize the FilePool
        """
        self.__pool: Dict[str, JsonFile] = {}

    def open(self, filepath: str, default: str = "{}") -> JsonFile:
        """
        Open a new file and store the current file in the FilePool
        :param filepath: File to open
        :param default: Default for file
        :return:
        """
        filepath = abs_filename(filepath)
        if filepath not in self.__pool:
            self.__pool[filepath] = JsonFile(filepath, default=default)
        return self.__pool[filepath]

    def sync(self):
        """
        Save configuration changes to disk.
        :return:
        """
        cli.simple_wait_fixed_time("Saving files, CRTL + C to abort [3s]", "Saved!", 3, green=True, vanish=True)
        for file in self.__pool.values():
            file.save()


pool = FilePool()
