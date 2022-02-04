from typing import Union, Dict

from .errors import report


def dict_str(field: Union[list, str]) -> list:
    if type(field) == str:
        return [field]
    return field


class FileAccessField:
    def __init__(self, field: Union[Dict[str, str], str]):
        if type(field) == str:
            self.filepath = field
            self.access_field = None
        else:
            self.filepath = field["file"]
            self.access_field = field["access"]

    def access(self, json: dict) -> Union[dict, str, int, list, None]:
        """
        Accesses a dict according to the URLAccessField rules.
        :param json: The json to access
        :return: The accessed field
        """
        if self.access_field is None:
            return json
        access = json
        for to_access in dict_str(self.access_field):
            try:
                access = access[to_access]
            except Exception as e:
                report(10, "FileAccesField accessing function",
                       "Could not access Json, some error occured. URL: " + self.filepath,
                       additional="dictionary: " + str(json) + " ; accessing " + str(
                           dict_str(self.access_field)) + " ; trying to access " + str(to_access) + " in " + access,
                       exception=e)
                return None
        return access

    def update(self, json: dict, new_value: Union[dict, str, int, list]):
        """
        Accesses a dict according to URLAccessField rules and updates it.
        :param json:
        :param new_value:
        :return:
        """
        if self.access_field is None:
            json = new_value
        access = json
        for to_access in dict_str(self.access_field):
            try:
                access = access[to_access]
            except Exception as e:
                report(10, "FileAccesField accessing function",
                       "Could not access Json, some error occured. URL: " + self.filepath,
                       additional="dictionary: " + str(json) + " ; accessing " + str(
                           dict_str(self.access_field)) + " ; trying to access " + str(to_access) + " in " + access,
                       exception=e)
                return
        # Does this even work? TODO
        access = new_value
