from typing import Dict

from requests import Response
from requests import get

requests: Dict[str, Response] = {}


def get_cached(url: str, headers: dict, enable_caching: bool) -> Response:
    if url in requests and enable_caching:
        return requests[url]
    result = get(url, headers=headers)
    requests[url] = result
    return result
