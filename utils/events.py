"""
The main file for handling events (positive errors ;))
"""
from .json_file import JsonFile


def report(sender: str, event: str, additional: str = ""):
    """
    Report a mew event
    :param sender: sender of evet
    :param event: event description
    :param additional: additional information
    :return:
    """
    events = JsonFile("data/events.json", default="[]")

    events.json.append({"sender": sender, "event": event, "additional": additional})
    events.save()
