"""
Basic IO operations
"""
from os import path, stat, makedirs
from typing import TextIO


def abs_filename(file: str) -> str:
    """
    Return the absolute filename
    :param file: File to get absolute path
    :return: absolute path
    """
    return path.abspath(file)


def generate(file: str, default: str = "{}") -> bool:
    """
    check a file and generate if it doesn't exist
    :param file: file to generate
    :param default: default to write to file
    :return: weather or not file has existed (will now exist)
    """
    if path.exists(file):
        if not stat(file).st_size < len(default.encode('utf-8')):
            return True
    else:
        makedirs(path.dirname(file), exist_ok=True)
    file = open(file, "w+")
    file.write(default)
    file.close()
    return False


def check(file: str) -> bool:
    """
    Check if a file exists
    :param file: file to check
    :return: weather or not the file exists
    """
    return path.exists(file)


def load(file: str, mode: str = "r", default: str = "{}") -> TextIO:
    """
    Open a file using python
    :param file: file to open
    :param mode: mode to open file with
    :param default: default to write to file (if nonexistent or too small)
    :return: a writeable python file
    """
    generate(file, default)
    return open(file, mode)
