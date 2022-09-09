import json
from typing import Union, Dict, List

from .io import abs_filename, load


class JsonFile:
    def __init__(self, filename: str, default: Union[str, Dict, List, int, float, bool] = "{}"):
        self.__filename = abs_filename(filename)
        if type(default) is not str:
            default = json.dumps(default, indent=4, sort_keys=True)
        json_file = load(self.__filename, default=default)
        self.json: Union[dict, list] = json.load(json_file)
        json_file.close()

    def reload(self):
        with load(self.__filename) as json_file:
            self.json = json.load(json_file)

    def save(self):
        with load(self.__filename, mode="w") as json_file:
            json.dump(self.json, json_file, indent=4, sort_keys=True)
