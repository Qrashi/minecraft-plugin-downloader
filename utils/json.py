import json

from .io import abs_filename, load


class JsonFile:
    def __init__(self, filename: str, default: str = "{}"):
        self.__filename = abs_filename(filename)
        json_file = load(self.__filename, default=default)
        self.json = json.load(json_file)
        json_file.close()

    def reload(self):
        with load(self.__filename) as json_file:
            self.json = json.load(json_file)

    def save(self):
        with load(self.__filename, mode="w") as json_file:
            json.dump(self.json, json_file, indent=4, sort_keys=True)
