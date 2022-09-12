from typing import Dict, List, Union

from requests import get

from .context_manager import context
from .errors import report

requests: Dict[str, Union[Dict, List, str, int, float, bool, None]] = {}


def get_managed(url: str, headers: dict) -> Union[Dict, List, str, int, float, bool, None, Exception]:
    if url in requests:
        return requests[url]
    else:
        try:
            request = get(url, headers=headers)
        except Exception as e:
            report(context.failure_severity, f"WebManager - {context.software} - {context.task}",
                   "could not complete request - an error occurred.", exception=e, software=context.software,
                   additional=f"URL: {url}")
            return e
        if request.status_code != 200:
            report(context.failure_severity, f"WebManager - {context.software} - {context.task}",
                   f"could not complete request - status code {request.status_code}", software=context.software,
                   additional=f"URL: {url}")
            return FaultyStatusCodeException(f"could not complete request - status code {request.status_code}")
        requests[url] = request.json()
        return requests[url]


class FaultyStatusCodeException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
