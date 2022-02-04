from hashlib import sha224
from os import path

from .errors import report


def get_hash(filename: str) -> str:
    if not path.exists(filename):
        report(3, "Hashing utility", "File to get hash of does not exist.", additional="File: " + filename)
        return "invalid file!"
    try:
        with open(filename, "rb") as file:
            file_bytes = file.read()
            return sha224(file_bytes).hexdigest()
    except Exception as e:
        report(3, "Hashing utility",
               "There was an error while trying to get the hash for a file. This will cause all plugins to get copied constantly resulting in higher copy times. This error is not critical.",
               additional="File: " + filename, exception=e)
        return "Exception while hashing"
