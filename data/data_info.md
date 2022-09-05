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
You may back up stored errors to an archive using ``archive.py``

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
You may back up stored events to an archive using ``archive.py``

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
N       blocking: {
N           game_version: { version attempted to update to
N               software: int; timestamp since the software has first blocked the update (software is software name)s
N           }
N       }
N       on_update: [
N           Tasks to do on server updating to a new version
N           You may use variables in every line that has been marked with an A:
N           * You may use %old_version%
N           * You may use %new_version%
N           {
N               tasks (see in sources.json)
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
    software: {
        dependency: {
            enabled: boolean
            copy_path: Path to copy to (with "/" at the beginning)
        }
        dependency: {
            enabled: boolean
            copy_path: Path to copy to (with "/" at the beginning)
        }
        ...
        ...
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

A at the start of a line indicates support for replacing non-static information like new version buildID

source: {
N   cache_results: Enable / disable usage of request result cache; boolean
    server: The name of the API / server to download from in text (e.g: "paper API")
N   headers: The headers to use. Useful for authentification
N   compatibility:
        remote: URLAccess field to an array of (compatible) versions
        behaviour: How to handle this array / string
            If the URL points to a ARRAY of compatible versions:
                "all|minor": All versions in this array are compatible with the software ("1.6 - 1.8") ALERT: Wont include higher 1.8 versions
                "max|minor": Only the EXACT newest version is compatible with the software (only uses the highest version from the versions array "1.17") 
                "all|major": All versions and minor versions of maximum version are compatible (would convert "1.6 - 1.8" to "1.6 - 1.8.99")
                "max|major": All minor versions for the maximum major versions are compatible (converts "1.17 - 1.17" to "1.17 - 1.17.99")
                "extend|major": Extend the previous up to the newest highest possible minimum version for the major version
                "extend|minor": Extend to the hightes exact version.
            If the URL points to a SINGLE compatible version
                "precise|major": All minor versions for the major versions are supported: "1.17" > "1.17 - 1.17.99"
                "extend|major": Extend the previous compatibility to the maximum minor version of the recieved major version; "1.14 - 1.17.1" + "1.18" > "1.14 - 1.18.99"
                "extend|minor": Extend the previous compatibility to the recieved version; "1.14 - 1.17.1" + "1.18" > "1.14 - 1.18"
                "precise|minor": Only support the recieved version.
    build: {
A       download: The URL to download a specific version from
            You may use %build% for the newest build number.
            You may use %newest_version% for the newest detected compatible version
            If there is no way to check for the latest compatible version, %newest_version% will be replaced with the newest game version.
            You may use %artifact% for the artifact name.
        local: The local build ID. Read below for type info.
N       name: The URL to fetch the artifact name
            You may use %build% for the newest build number.
            You may use %newest_version% for the newest detected compatible version
            If there is no way to check for the latest compatible version, %newest_version% will be replaced with the newest game version.
        remote: The URL to download build information from.
            NOTE: If the URL returns a single build id which is the newest
            it can be a string Build ID.
    }
    tasks: {
N       enabled: Enable tasks to execute after downloading the newest build
        copy_downloaded: boolean; copy the downloaded file into tmp directory
        cleanup: boolean; clean up the files after an error (good for investigating errors)
        tasks: [
            {
N               enabled: wether task is enabled
                type: Type of task; Types of tasks e.g "run"
                    * run: Run a console command in the tmp directory (os.system)
                    * end: Specify what to do at the end of all tasks (optional)
                    * write: Write stuff to a jsonFile
                
                value: Options for the tasks:
A                   * if type is run: requires what to run example: "run": "java -jar xy.jar"
                        You may use %build% for the newest build number.
                        You may use %newest_version% for the newest detected compatible version
                        If there is no way to check for the latest compatible version, %newest_version% will be replaced with the newest game version.
                    so value = e.g "java -jar blah.jar"
                    
                    * end: the file to replace the downloaded file with, keep the tmp folder or not; example:
                        {
    A                       file: (optional) the file to replace the previously downloaded file with !NO "/" before the name! (for example "paper_1.17.1.jar" will replace the contents of the downloaded file with the contents of "paper_1.17.1.jar")
    A                       keep: (optional) the path to copy the tmp directory to (for exaple "/home/minecraft/builds/%build%" will create the %build% directory and copy the contents of tmp into it.)
                                You may use %build% for the newest build number.
                                You may use %newest_version% for the newest detected compatible version
                                If there is no way to check for the latest compatible version, %newest_version% will be replaced with the newest game version.
                                                    
                            Please note that there is no way to "offically" keep the tmp directory in order to keep the software folder clean.
                        }
                    so value = e.g {"file": "blah.file", "keep": "blah.blah"}
                    
                    * write: The file to write to; a list of things to change.
                    {
A                       file: filename (must be of json format)
                        changes: [
                            {
A                               path: Path to field that requires a change e.g ["builds", "downloaded"] (can create values)
A                               value: The new value
                                    You may use %build% for the newest build number.
                                    You may use %newest_version% for the newest detected compatible version
                                    If there is no way to check for the latest compatible version, %newest_version% will be replaced with the newest game version.                           
                                
                                This works similar to JSONAccessField
                        ]
                    }
                    
                    so value = e.g {"file": "file.file", "changes": {"path": [server_info", "version"], "value": "1.18.1"}}
                progress: {
                    value: What percentage to display in the progress bar (0 - 100) e.g 57
                    message: What message to display in the progress bar e.g "Patching vanilla server..."
                }
                
            }
        ]
    }
    last_checked: The last time the sourcce has been checked
}
```

### config.json

```
config.json: {
    batch_size: Batch size for copying (amount of RAM the copy operation will take)
    sources_folder: Software folder (Where all software is stored)
    newest_game_version: URLAccessField to retrieve the latest game version.
    version_check_interval: The interval (in days) between game version checks.
    git_auto_update: boolean; Try to automatically download newest version from git
    default_header: The default header to use (dict)
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
