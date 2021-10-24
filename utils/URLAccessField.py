from typing import Union, Dict


def dict_str(field: Union[list, str]) -> list:
    if type(field) == str:
        return [field]
    return field


class URLAccessField:
    def __init__(self, field: Union[Dict[str, str], str]):
        if type(field) == str:
            self.url = field
            self.access_field = None
        else:
            self.url = field["URL"]
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
            access = access[to_access]
        return access
