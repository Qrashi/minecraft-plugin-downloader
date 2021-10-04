# Documentation

This is a little documentation for the data structures used in these scripts:

#### Explanation: <br>

```N``` at the start of a line: This field is **not required**! <br>
```P``` at the start of a line: This field supports REPLACING, see below.

#### General data types:

* URLAccessField:
  * Advantages:
    * Specifies which part of a response the programm should use
    * e.g a URL returns a dict and we only want to use a specific field
    * Or even if the field is buried inside of multiple other fields
    * Easy to use, even just a URL is enough
  * Syntax
    * No need to access a specific field:
    ```
    field: URL
    ```
    * Need to access a specific field
    ```
    field: {
      URL: URL to retrieve
      access: [
        field (string),
        field (string),
        ...  
      ]
    }
    ```
    Imagine this is the response to a version query:
     ```json
    {
    "info": {
      "versions:": [111,123,231]
    },
    "status":  "OK"
    }    
    ```
    To access the "versions" field, you would use the following URLAccessField:
    ```json
    {
      "URL": "https://blah.blah.blah",
      "access":  [
        "info",
        "versions"  
      ]
    }    
    ```
    You can use a URLAccessField in every URL field. If you can't use one, it will be marked with a ```A``` letter at
    the start of the line.
  * A fine example of this type in use can be seen in the config.json file.

### errors.json

Stores occurred errors.

```
errors.json: [error, error, error, ...]

error: {
    from: Sender of error (Updater, Download)
    reason: Reason of error in clear text
    severity: Importance of error
    time: Time of error, as text
    stamp: Time of error, as timestamp
    additional: Additional information
    exception: The occurred exception (default: <class 'Exception'>
}
```

### events.json

Stores occurred events.

```
events.json: [event, event, event, ...]

event: {
    event: Type of event in clear text
    sender: Sender of event (Updater, Download)
    additional: Additional information
}
```

### servers.json

Stores server information and configuration.

```
servers.json: {name: server, name: server, name: server, ...}

server: {
N   auto_update: {
N       enabled: boolean
N       blocking: [
N           blocking_software: {
N               name: Name of software
N               since: First time the software has blocked upgrade (timestamp)
N           }
N       ]
N   }
    path: Path to server ROOT directory
    version: Version as a string
    software: {
        name: { # Name = name of dependency
            copy_path: path to copy to WITHOUT /! (e.g "paper.jar")
            enabled: boolean
        }
    }
    hardware: {
        port: port number
        screen: The screen to connect to, automatically generated.
        ram: The RAM specified in the start.sh file
        start: The start script filename WITHOUT /! (e.g: "start.sh")
        java: Java version (NEWEST or 8)
    }
}
```

### software.json

Stores information on the available software, only local things

```
software.json: {name: software, name: software, name: software, ...}

software: {
    file: filename in software folder
    hash: The last recorded hash for the file (used to check for changes)
    identifier: A description of the software (e.g: "Minecraft server / paper")
    severity: How severe a possible error
    # Requires match is REQUIRED, but a empty body is enough.
    requirements: { Describes which versions this plugin is compatible with.
N       min: Oldest supoported version
N       max: Newest supported version
    }
    version: The latest downloaded version (if the plugin has been built against a specific version)
    This is required when the software has a source and is tagged renewable (newest key in sources.json)
    If there is no "newest" field in the sources json, this will get used instead 
}
```

### sources.json

This files stores data on how to download new software versions

```
sources.json: {name: source, name: source, name: source, ...}

source: {
    server: The name of the API / server to download from in text (e.g: "paper API")
N   newest: {
PN      remote: The URL to download information on the latest version (see example)
PN      acess: The json field to access (remove key for no field)

N           EXAMPLE:
N           remote: https://papermc.io/api/v2/projects/waterfall/
N           This gives a json object with a property called "versions"       
N           acess: versions
N           Will tell the programm to acess the versions field.

N           The data from these sites will be compared and the highest avialible version will be picked.
N           You may use %newest_major% or %newest_minor% in future URLS.
N           If the remote version is higher than the local version, the plugin requirement and version will be updated.
N   }
N   previous_version: The version that was detected on the previous run / used to display "update" messages.
    build: {
PA      download: The URL to download a specific version from
P           You may use %build% for the newest build number.
P           You may use %newest_version% for the newest detected compatible version
        local: The local build ID
P       remote: The URL to download build information from.
    }
   last_checked: The last time the sourcce has been checked
}
```

## REPLACING

### config.json

Static information, this file also stores values that can be replaced <br>
fields marked with a ```P``` at the start of the line.

```
config.json: {
    batch_size: Batch size for copying (amount of RAM the copy operation will take)
    sources_folder: Software folder (Where all software is stored)
    start_requirements: {
        CPU: Amount of CPU that needs to avialible to start ANY server 
        RAM: Amount of RAM that needs to avialible to start ANY server
    }
    java_paths: {
        NEWEST: Path to newest java version
        "8": Path to java 8
N       *****: Any other java version 
    }
    newest_game_version: URL to retrieve the latest game version.
    version_check_interval: The interval (in days) between game version checks.
}
```

Every field in this json file can be used in ```P``` marked fields. Simply put ```%field%``` (or if it is a nested
field ```%parent_child%``` > so ```%version_major%``` works.)

### versions.json

Information on all the existing game versions, will work automatically

```
{
    last_check: The days since epoch at the date of the last check
    current_version: Current game version (version object)
    versions: [
        version (sting),
        version (sting),
        ...
    ]
}
```
