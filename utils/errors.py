from datetime import datetime
from json import dumps
from typing import Union

from .json import JsonFile


def report(severity: int, sender: str, reason: str, additional: str = "",
           exception: Union[Exception, str] = "No exception provided."):
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
