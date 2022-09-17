"""
The main file for handling events (positive errors ;))
"""
from singlejson import JSONFile


def report(sender: str, event: str, additional: str = ""):
    """
    Report a mew event
    :param sender: sender of evet
    :param event: event description
    :param additional: additional information
    :return:
    """
    events = JSONFile("data/events.json", default="[]")

    events.json.append({"sender": sender, "event": event, "additional": additional})
    events.save()
