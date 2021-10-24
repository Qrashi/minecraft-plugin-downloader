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
N       enabled: boolean > true or false
N       blocking: [
N           blocking_software: {
N               name: Name of software
N               since: First time the software has blocked upgrade (timestamp)
N           }
N       ]
N   }
    path: Path to server ROOT directory
    version: {
        type: Either "version" or "file"
        value: 
             If version: The version as a string
             If file: {
                  file: path to file
                  access: How to navigate to the version string (like in URLAccessField)
             }
        Hardware won't be used by the script itself, so you can add custom tags like
        port
        java
        or whatever you like into it to use with other software.
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
}
```

### sources.json

This files stores data on how to download new software versions

```
sources.json: {name: source, name: source, name: source, ...}

source: {
    server: The name of the API / server to download from in text (e.g: "paper API")
N   compatibility:
        remote: URLAccess field to an array of (compatible) versions
        behaviour: How to handle this array
            "all|precise": All versions in this array are compatible with the software ("1.6 - 1.8") ALERT: Wont include higher 1.8 versions
            "max|precise": Only the newest version is compatible with the software (only uses "1.17 - 1.17") 
            "all|max": All versions and minor versions of maximum version are compatible (would convert "1.6 - 1.8" to "1.6 - 1.8.99")
            "max|max": All minor versions for the maximum maor versions are compatible (converts "1.17 - 1.17" to "1.17 - 1.17.99")
    build: {
A       download: The URL to download a specific version from
            You may use %build% for the newest build number.
            You may use %newest_version% for the newest detected compatible version
            If there is no way to check for the latest compatible version, %newest_version% will be replaced with the newest game version.
            You may use %artifact% for the artifact name.
        local: The local build ID AS AN INTEGER!
N       name: The URL to fetch the artifact name
            You may use %build% for the newest build number.
            You may use %newest_version% for the newest detected compatible version
            If there is no way to check for the latest compatible version, %newest_version% will be replaced with the newest game version.
        remote: The URL to download build information from.
    }
   last_checked: The last time the sourcce has been checked
}
```

### config.json

```
config.json: {
    batch_size: Batch size for copying (amount of RAM the copy operation will take)
    sources_folder: Software folder (Where all software is stored)
    newest_game_version: URL to retrieve the latest game version.
    version_check_interval: The interval (in days) between game version checks.
}
```

### versions.json

Information on all the existing game versions, will work automatically

```
{
    last_check: The days since epoch at the date of the last check
    current_version: Current game version (version object)
    versions: [
        version (string),
        version (string),
        ...
    ]
}
```
