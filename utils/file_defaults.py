CONFIG = {
  "batch_size": 4096,
  "git_auto_update": True,
  "newest_game_version": {
    "task": "get_return",
    "url": "https://www.papermc.io/api/v2/projects/paper",
    "path": [
      "versions"
    ]
  },
  "sources_folder": "software",
  "version_check_interval": 3,
  "default_headers": {
    "User-Agent": "minecraft-plugin-downloader (github/qrashi/...) - automated service"
  },
  "config_version": 1
}
