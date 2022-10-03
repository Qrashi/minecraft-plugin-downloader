[![DeepSource](https://deepsource.io/gh/Qrashi/minecraft-plugin-downloader.svg/?label=active+issues&show_trend=true&token=YZB2mvViWt3uIzoSt5pLF6Pe)](https://deepsource.io/gh/Qrashi/minecraft-plugin-downloader/?ref=repository-badge)
# minecraft plugin downloader
![minecraft-plugin-downloader](https://user-images.githubusercontent.com/56923218/192155894-1346d39b-6d1e-473d-9be3-7375d1caed6d.gif)
This set of small python scripts is aimed to help you manage your server plugins.

It is primarily used by me to automatically update my server. Expect breaking changes when I want to make some or broken software (since I don't test before I commit...)

## Features

* Every plugin has a "version requirement" - and a plugin will only get copied into servers supporting the "
  requirements".
    * The plugin is also able to detect "increments" of these requirements automatically.
* Can auto-detect if a file has been changed locally or a new build has been released
* Task system
* Convenient WebAccessField syntax

## Installation

1. Clone the repository. (```git clone https://github.com/Qrashi/minecraft-plugin-downloader.git```)
2. Install the requirements: <br>```pip install -r requirements.txt``` 
3. Execute ```update.py```. This will generate all default configurations, create the default servers directory and download information about current minecraft versons from the paper-api.

#### First time setup requires an internet connection to fetch minecraft versions. 

## Adding the first dependency

1. Download your software / dependency / plugin.
2. Put the dependency into the software folder (name of folder can be changed in `config.json`)
3. Execute ```manager.py``` and follow the given instructions.

## Upgrading a dependency

If you would like for the script to **auto-download** new versions of pugins, please refer to `data_info.md` and `examples.md`.
<br>Otherwise, 
* **replace** the old software with the new one (in the software folder).
* If you want to specify that this version of the software has other version compatibility than the old one, please **run** `manager.py` and follow the on-screen instructions.
* Next time you execute `update.py`, the program will notify that it has detected changes to the software.

## Removing a dependency

1. If you would like to remove a dependency, please delete it from the software folder.
2. Run `manager.py` and follow the on-screen instructions.

## Adding your first server

TODO

#### Example configurations can be found in the examples.md file

For a more detailed overview of the different json files, please view the `data_info.md` file in "data/"
