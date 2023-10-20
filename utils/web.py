"""
manage web requests
"""
from typing import Dict, List, Union
from singlejson import load

from requests import get

import utils.cli as cli
from utils.file_defaults import CONFIG
from .context_manager import context
from .errors import report


config = load("data/config.json", default=CONFIG).json
requests: Dict[str, Union[Dict, List, str, int, float, bool, None]] = {}


def get_managed(url: str, headers: dict) -> Union[Dict, List, str, int, float, bool, None, Exception]:
    """
    Get data from the internet, cached, with easy - to rea errors
    :param url: URL to retrieve data from
    :param headers: headers to use
    :return: the desired data or an exception (check using isinstance Exception)
    """
    if url in requests:
        return requests[url]
    try:
        if config["debug"]:
            cli.info(f"fetching url {url} - {context.name}")
        request = get(url, headers=headers)
    except Exception as e:
        report(context.failure_severity, f"WebManager - {context.name} - {context.task}",
               "could not complete request - an error occurred.", exception=e, software=context.name,
               additional=f"URL: {url}")
        return e
    if request.status_code != 200:
        report(context.failure_severity, f"WebManager - {context.name} - {context.task}",
               f"could not complete request - status code {request.status_code}", software=context.name,
               additional=f"URL: {url}")
        return FaultyStatusCodeException(f"could not complete request - status code {request.status_code}")
    requests[url] = request.json()
    return requests[url]


class FaultyStatusCodeException(Exception):
    """
    An error describing some error in the GET process
    """
