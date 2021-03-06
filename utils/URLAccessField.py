from typing import Union, Dict

from .errors import report


def dict_str(field: Union[list, str]) -> list:
    if type(field) is str:
        return [field]
    return field


class URLAccessField:
    def __init__(self, field: Union[Dict[str, str], str]):
        if type(field) is str:
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
                report(10, "JsonField accessing function",
                       "Could not access json, some error occurred. URL: " + self.url,
                       additional="dictionary: " + str(json) + " ; accessing " + str(
                           dict_str(self.access_field)) + " ; trying to access " + str(to_access) + " in " + str(
                           access),
                       exception=e)
                return None
        return access
