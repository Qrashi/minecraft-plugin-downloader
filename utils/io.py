from os import path, stat, makedirs
from typing import TextIO


def abs_filename(file: str) -> str:
    return path.abspath(file)


def generate(file: str, default: str = "{}") -> bool:
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
    return path.exists(file)


def load(file: str, mode: str = "r", default: str = "{}") -> TextIO:
    generate(file, default)
    return open(file, mode)
