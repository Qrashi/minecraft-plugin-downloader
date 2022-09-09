# Auto update

## The perfect auto update lifecycle

### Example: Any spigot plugin (Vault)

To get the newest version, we first have to retrieve the newest compatible version. We do that by setting "check" in sources.json to "always" so the software will ALWAYS check the compatibility first.
<br> Here is what minecraft-plugin-downloader is told to do:

1. The compatible versions (set by the developer) get fetched from the **spiget API**
   1. We want the compatible versions to be checked every time, so we use "always" as the option for "check"
   2. The correct url is used in a SINGLE get_return task
   3. The behaviour is set to "all|major" so ALL received versions ("1.14 - 1.17") INCLUDING all higher versions of
      1.17 (1.17.1, 1.17.2) are **COMPATIBLE**
2. The versionID of the latest version is fetched using, again a single get_return task and if it is any different
3. -> the newest build gets downloaded (we need to return the URL to download so we only use a return task that returns the valid URL)

Configurations for the Vault example
<br>``software.json``

```json
{
   "vault": {
        "file": "vault.jar",
        "hash": "",
        "identifier": "User data management / vault",
        "requirements": {
            "max": "1.17",
            "min": "1.13"
        },
        "severity": 7
    }
}
```

``sources.json``

```json
{
   "vault": {
        "build": {
            "download": "https://www.spigotmc.org/resources/vault.34315/download?version=%build%",
            "local": 344916,
            "remote": {
               "task": "get_return",
                "url": "https://api.spiget.org/v2/resources/34315/versions/latest",
                "path": [
                    "id"
                ]
            }
        },
        "compatibility": {
            "behaviour": "all|max",
           "check": "always",
            "remote": {
               "task": "get_return",
                "url": "https://api.spiget.org/v2/resources/34315",
                "path": [
                    "testedVersions"
                ]
            }
        },
        "last_checked": "Never. Config issue?",
        "server": "Spiget API"
    }
}
```

Unfortunately this does not work due to the DDOS detection of spigot.

### Example: paper

1. The newest build ID is fetched
   2. We don't need to include a "task": "get_return" field here since it is the default.
2. If the newest build is different to the one on the disk, the newest compatibility is fetched
   1. The behaviour is set to "precise|minor" so ONLY the highest received version is compatible
   2. The check option is set to "build" to only check for new compatibility if a new build has been published
3. The URL to the newest build is retrieved
   1. It is also possible to directly use a get_return task to get the build download url - but in order to demonstrate get_store i used get_store here.
4. The newest build gets downloaded

Configuration for this "perfect example":
<br>``software.json``

```json
 {
   "paper": {
      "file": "paper.jar",
      "hash": "",
      "identifier": "Minecraft server / paper",
      "requirements": {
         "max": "1.17.1",
         "min": "1.17.1"
      },
      "severity": 10
   }
}
```

``sources.json``

```json
{
  "paper": {
     "compatibility": {
        "behaviour": "precise|minor",
        "check": "build",
        "remote": {
           "url": "https://papermc.io/api/v2/projects/paper/",
           "path": ["versions"],
           "task": "get_return"
        }
     },
     "server": "paper API",
     "build": {
        "download": [
           {
              "task": "get_store",
              "url": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%/builds/%build%",
              "path": [
                 "downloads",
                 "application", 
                 "name"
              ],
              "destination": "artifact_name"
           },
           {
              "task": "return",
              "value": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%/builds/%build%/downloads/%artifact_name%"
           }
        ],
        "local": 299,
        "remote": {
          "url": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%",
          "path": ["builds"]
        }
     },
     "last_checked": "Never"
  }
}
```

You can also add tasks that get executed after a new build has been downloaded. The syntax is like this:
```json
"tasks": [
{
        "type": "run",
        "value": "java -jar example.jar"
}
]
```

