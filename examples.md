# Auto update

## The perfect auto update lifecycle

###Example: Any spigot plugin (Vault)
1. The compatible versions (set by the developer) get fetched from the spiget API
   1. The behaviour is set to "max|max" so ALL received versions ("1.14 - 1.17") INCLUDING all higher versions of 1.17 (1.17.1, 1.17.2) are **COMPATIBLE** 
   2. If the compatibility is different from the last check, an event gets reported
2. The versionID of the latest version is fetched and compared against the local version
3. The newest build gets downloaded
4. The newest build gets put into all the servers.

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
                "URL": "https://api.spiget.org/v2/resources/34315/versions/latest",
                "access": [
                    "id"
                ]
            }
        },
        "compatibility": {
            "behaviour": "all|max",
            "remote": {
                "URL": "https://api.spiget.org/v2/resources/34315",
                "access": [
                    "testedVersions"
                ]
            }
        },
        "last_checked": "Never. Config issue?",
        "server": "Spiget API"
    }
}
```
###Example: paper
1. The versions paper was built against are fetched
   1. The behaviour is set to "max|precise" so ONLY the highest received version is compatible
2. All builds for the newest detected fetched version get fetched
3. The newest build gets downloaded
4. The newest build gets put into all the servers.

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
        "URL": "https://papermc.io/api/v2/projects/paper/",
        "access": ["versions"]
     },
     "server": "paper API",
     "build": {
        "download": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%/builds/%build%/downloads/%artifact%",
        "local": 299,
        "remote": {
          "URL": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%",
          "access": ["builds"]
        },
        "name": {
           "URL": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%/builds/%build%",
           "access": [
              "downloads",
              "application",
              "name"
           ]
        }
     },
     "last_checked": "Never"
  }
}
```

## Almost perfect examples
###Example: LuckPerms

1. The latestSuccessful build ID for LuckPerms get fetched and if different to the local ID,
2. The newest build gets downloaded
3. The newest build gets put into all the servers.

This configuration WON'T update the versions that the dependency is compatible with.
<br> I have set the minumum required version to 1.0 and the maximum to 1.99 because LuckPerms works with almost every mineceraft version.

But an anticheat plugin for example that REQUIRES specific versions, requires you to manually maintain its requirements.

Configuration for LuckPerms:
```json
{
   "LuckPermsBukkit": {
        "file": "LuckPermsBukkit.jar",
        "hash": "",
        "identifier": "Permission management / LuckPerms / Server-side",
        "requirements": {
            "max": "1.99",
            "min": "1.0"
        },
        "severity": 8
    }
}
```
``sources.json``
```json
{
   "LuckPermsBukkit": {
      "build": {
         "download": "https://ci.lucko.me/job/LuckPerms/%build%/artifact/%artifact%",
         "local": 1300,
         "name": {
            "URL": "https://ci.lucko.me/job/LuckPerms/%build%/api/json",
            "access": [
               "artifacts",
               0,
               "relativePath"
            ]
         },
         "remote": {
            "URL": "https://ci.lucko.me/job/LuckPerms/api/json",
            "access": [
               "lastSuccessfulBuild",
               "number"
            ]
         }
      },
      "last_checked": "Never - config issue?",
      "server": "Lucko Jenkins API"
   }
}
```

# No config at all
Having no auto-update config at all is also fine! The script automatically checks the checksums of the dependencies.
<br> You can just drop the newest versions of dependency x into the software folder and the script will distribute the file to all servers


# Static links
Later on, I will add support for static links (e.g dropbox links). You can then set a "interval" and the script will just download the file every xy Months / days.


# Tasks
Software like paper needs a small bit of processing before using (applying patches).
This can be done using tasks. The example below shows such a source.
``sources.json``
```json
{
   "paper": {
      "build": {
         "download": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%/builds/%build%/downloads/%artifact%",
         "local": 388,
         "name": {
            "URL": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%/builds/%build%",
            "access": [
               "downloads",
               "application",
               "name"
            ]
         },
         "remote": {
            "URL": "https://papermc.io/api/v2/projects/paper/versions/%newest_version%",
            "access": [
               "builds"
            ]
         }
      },
      "compatibility": {
         "behaviour": "max|precise",
         "remote": {
            "URL": "https://papermc.io/api/v2/projects/paper/",
            "access": [
               "versions"
            ]
         }
      },
      "last_checked": "10.23 17:47",
      "server": "paper API",
      "tasks": {
         "copy_downloaded": true,
         "enabled": true,
         "cleanup": true,
         "tasks": [
            {
               "progress": {
                  "message": "Patching vanilla server with paper patches",
                  "value": 10
               },
               "type": "run",
               "value": "java -Dpaperclip.patchonly=true -jar paper.jar"
            },
            {
               "progress": {
                  "message": "Copying patched jar",
                  "value": 90
               },
               "type": "end",
               "value": {
                  "file": "versions/%newest_version%/paper-%newest_version%.jar"
               }
            }
         ]
      }
   }
}
```
As you can see, the script will
1. Copy the downloaded file into the temporary folder
2. Patch the vanilla jar using "java -Dpaperclip.patchonly=true -jar paper.jar" and inform the user that it is doing so using the progress properties.
3. Copy the result back into the "software" folder.
4. If one of these tasks fails, it will delete the temporary files (You can also set this to false to better debug errors)