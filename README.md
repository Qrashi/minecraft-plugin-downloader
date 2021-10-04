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