[![DeepSource](https://deepsource.io/gh/Qrashi/minecraft-plugin-downloader.svg/?label=active+issues&show_trend=true&token=YZB2mvViWt3uIzoSt5pLF6Pe)](https://deepsource.io/gh/Qrashi/minecraft-plugin-downloader/?ref=repository-badge)
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

![minecraft-plugin-downloader](https://user-images.githubusercontent.com/56923218/192155894-1346d39b-6d1e-473d-9be3-7375d1caed6d.gif)

## Installation

1. Clone the repository. (```git clone https://github.com/Qrashi/minecraft-plugin-downloader.git```)
2. Execute ```pip install -r requirements.txt``` to install all dependencies
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

#### Example configurations can be found in the examples.md file

For a more detailed overview of the different json files, please view the "data_info.md" file in "data/"
