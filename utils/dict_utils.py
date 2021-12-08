def enabled(json: dict) -> bool:
    if "enabled" in json:
        return json["enabled"]
    return True
