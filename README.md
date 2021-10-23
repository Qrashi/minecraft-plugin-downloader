# minecraft plugin downloader

This set of small python scripts is aimed to help you manage your server plugins.

## Features

* Every plugin has a "version requirement" - and a plugin will only get copied into servers supporting the "
  requirements".
    * The plugin is also able to detect "increments" of these requirements automatically.
* Can auto-detect if a file has been changed locally or a new build has been released
* Very stable, reliable error handling
* Pretty CLI interface :)
* Clear entry end exit point, easy to embed


## Installation

1. Clone the repository. (```git clone https://github.com/Qrashi/minecraft-plugin-downloader.git```)
2. Execute ```pip -r requirements.txt``` to install all dependencies
3. If you are using this script on Windows, please enable the ```windows_compatibility``` option in ```config.json```
4. Execute ```update.py```. This will
   1. Generate configuration files
   2. Download minecraft version information (by default) from the paper API
### Important
The first time setup **REQUIRES** an internet connection in order to fetch basic minecraft information!

## Adding the first dependency

1. Download your software.
2. Copy the dependency into the software folder (name of folder can be changed in config.json)
3. Rename the file to a clean name (```paper.jar``` instead of ```paper-1.17-501.jar```)
4. Execute ```manage_software.py``` and follow the instructions

#### Example configurations can be found in the auto_update.md file