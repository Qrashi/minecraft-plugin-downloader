from typing import Union, Dict
from .error import report


def dict_str(field: Union[list, str]) -> list:
    if type(field) == str:
        return [field]
    return field


class URLAccessField:
    def __init__(self, field: Union[Dict[str, str], str]):
        if type(field) == str:
            self.url: str = field
            self.access_field = None
        else:
            self.url: str = field["URL"]
            self.access_field = field["access"]

    def access(self, json: dict):
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
                report("JsonField accessing function", 10, "Could not access Json, some error occured. URL: " + self.url, exception=e, additional="dictionary: " + str(json) + " ; accessing " + str(dict_str(self.access_field)) + " ; trying to access " + str(to_access) + " in " + access)
                return None
        return access
