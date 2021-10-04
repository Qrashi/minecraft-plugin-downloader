from typing import Union, Dict


class URLAccessField:
    def __init__(self, field: Union[Dict[str, str], str]):
        if type(field) == str:
            self.url = field
            self.access_field = None
        else:
            self.url = field["URL"]
            self.access_field = field["access"]

    def access(self, json: dict) -> dict:
        """
        Accesses a dict according to the URLAccessField rules.
        :param json: The json to access
        :return: The accessed field
        """
        if self.access_field is None:
            return json
        access = json
        for to_access in self.access_field:
            access = json[to_access]
        return access
