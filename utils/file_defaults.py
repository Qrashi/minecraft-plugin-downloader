"""
This file stores static default file information
"""

CONFIG = {
    "batch_size": 4096,
    "git_auto_update": True,
    "newest_game_version": {
        "url": "https://www.papermc.io/api/v2/projects/paper",
        "path": [
            "versions"
        ]
    },
    "sources_folder": "software",
    "version_check_interval": 3,
    "debug": False,
    "default_headers": {
        "User-Agent": "minecraft-plugin-downloader (github/qrashi/...) - automated service"
    },
    "config_version": 3
}

VERSIONS = {
    "current_version": "1.0",
    "last_check": 0,
    "versions": [],
    "known_malformed_versions": [
        "3D Shareware v1.34"
    ]
}
