"""
Hashing utilities
"""
from hashlib import sha224
from os import path

from .errors import report
from .context_manager import context


def get_hash(filename: str) -> str:
    """
    Get the hash of a file
    :param filename: file to get hash of
    :return: hash (str)
    """
    if not path.exists(filename):
        report(context.failure_severity, "Hashing utility",
               f"File to get hash of does not exist. - updating {context.name}", additional="File: " + filename)
        return "invalid file!"
    try:
        with open(filename, "rb") as file:
            file_bytes = file.read()
            return sha224(file_bytes).hexdigest()
    except Exception as e:
        report(int(context.failure_severity / 4), "Hashing utility",
               f"There was an error while trying to get the hash for a file. This will cause all plugins to get copied constantly resulting in higher copy times. This error is not critical. {context.name}",
               additional="File: " + filename, exception=e)
        return "Exception while hashing"
