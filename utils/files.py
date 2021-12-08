from typing import Dict

from .cli_provider import cli
from .io import abs_filename
from .json import JsonFile

if __name__ == "__main__":
    print("The file pool is only meant to be imported!")
    exit()


class FilePool:
    def __init__(self):
        self.__pool: Dict[str, JsonFile] = {}

    def open(self, filepath: str, default: str = "{}") -> JsonFile:
        filepath = abs_filename(filepath)
        if filepath not in self.__pool:
            self.__pool[filepath] = JsonFile(filepath, default=default)
        return self.__pool[filepath]

    def sync(self):
        cli.simple_wait_fixed_time("Saving files, CRTL + C to abort [3s]", "Saved!", 3)
        for file in self.__pool.values():
            file.save()


pool = FilePool()
