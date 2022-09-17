"""
The main file for handling errors
"""
from datetime import datetime
from json import dumps
from typing import Union

from .static_info import VERSION, COMMIT
from .json_file import JsonFile


def report(severity: int, sender: str, reason: str, additional: str = "",
           exception: Union[Exception, str] = "No exception provided.", software: Union[str, None] = None):
    """
    Report a new error
    :param severity: severity of error (0 - 10)
    :param sender: sender of error (web download, write task)
    :param reason: reason for error
    :param additional: additional information
    :param exception: thrown exception
    :param software: software where error was caused
    :return:
    """
    errors = JsonFile("data/errors.json", default="[]")

    time = datetime.now().strftime("%d.%m %H:%M:%S")
    stamp = datetime.now().timestamp()

    # Try if exception is serializable
    # noinspection PyBroadException
    try:
        dumps(str(exception))
    except Exception:
        exception = "Could not save exception - not serializable!"

    if software is not None:
        try:
            from utils.files import pool
            all_sources = pool.open("data/sources.json", default="{}").json
            if software in all_sources:
                errors.json.append({"severity": severity, "reason": reason, "from": sender, "software": software,
                                    "last_successful_software_check": all_sources[software]["last_check"],
                                    "additional": additional, "time": time, "stamp": stamp, "exception": str(exception),
                                    "version": VERSION, "commit": COMMIT})
                return
        except Exception as _:
            errors.json.append({"severity": severity, "reason": reason, "from": sender, "software": software,
                                "additional": additional, "time": time, "stamp": stamp, "exception": str(exception),
                                "version": VERSION, "commit": COMMIT})
            return

    errors.json.append({"severity": severity, "reason": reason, "from": sender,
                        "additional": additional, "time": time, "stamp": stamp, "exception": str(exception),
                        "version": VERSION, "commit": COMMIT})

    errors.save()
