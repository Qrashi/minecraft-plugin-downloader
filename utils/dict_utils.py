"""
Some utilities for handling dictionaries
"""


def enabled(json: dict) -> bool:
    """
    Check if a field is enabled
    :param json: field to check
    :return: wether or not enabled is true or false if existent
    """
    if "enabled" in json:
        return json["enabled"]
    return True
