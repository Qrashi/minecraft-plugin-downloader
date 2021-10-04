from .cli_provider import cli
from .files import abs_filename
from .jsonFile import JsonFile

if __name__ == "__main__":
    print("Blas mir die huf auf")
    exit()


class FilePool:
    def __init__(self):
        self.__pool = {}

    def open(self, filepath: str, default="{}") -> JsonFile:
        filepath = abs_filename(filepath)
        if filepath not in self.__pool:
            self.__pool[filepath] = JsonFile(filepath, default=default)
        return self.__pool[filepath]

    def sync(self):
        cli.simple_wait_fixed_time("Saving configurations, CRTL + C to abort [3s]", "Saved!", 3, vanish=True)
        for file in self.__pool.values():
            file.save()


pool = FilePool()
