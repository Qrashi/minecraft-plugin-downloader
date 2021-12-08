from .json import JsonFile


def report(sender: str, event: str, additional: str = ""):
    events = JsonFile("data/events.json", default="[]")

    events.json.append({"sender": sender, "event": event, "additional": additional})
    events.save()
