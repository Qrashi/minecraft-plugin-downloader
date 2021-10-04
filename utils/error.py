from datetime import datetime
from json import dumps

from .jsonFile import JsonFile


def report(sender: str, severity: int, reason: str, additional="", exception=Exception):
    errors = JsonFile("data/errors.json", default="[]")

    time = datetime.now().strftime("%d.%m %H:%M:%S")
    stamp = datetime.now().timestamp()

    # Try if exception is serializable
    # noinspection PyBroadException
    try:
        dumps(str(exception))
    except Exception:
        exception = "Could not save exception - not serializable!"

    errors.json.append({"severity": severity, "reason": reason, "from": sender,
                        "additional": additional, "time": time, "stamp": stamp, "exception": str(exception)})

    errors.save()
