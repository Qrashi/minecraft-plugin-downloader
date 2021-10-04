from .jsonFile import JsonFile


def report(sender: str, event: str, additional=""):
    events = JsonFile("data/events.json", default="[]")

    events.json.append({"sender": sender, "event": event, "additional": additional})
    events.save()
