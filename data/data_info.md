# Documentation

This is a little documentation for the data structures used in these scripts:

#### Explanation: <br>

```N``` at the start of a line: This field is **not required**! <br>
```P``` at the start of a line: This field supports REPLACING, see below.<br>
```W``` at the start of a line: This field supports WebAccessFields, see below

#### General data types:

* URIAccessField:
    * Usage:
        * If you want to use only a specific part of a json dictionary, this will help you get the needed data
    * Syntax
        * The data is already the data you want:
      ```
      [] - this is a valid URIAccessField
      ```
        * The data is under "versions", "newest"
      ```
      [
          "versions",
          "newest"
      ]
      ```
      So if the FULL .json would look like this:
       ```json
      {
      "info": {
        "versions:": ["1.18","1.19","1.20"]
      },
      "status":  "OK"
      }    
      ```
      To return the LAST version you would do this:
      ```json
      [
        "info",
        "versions",
        -1
      ]    
      ```
    * A fine example of this type in use can be seen in the config.json file.

* WebAccessFields
  * WebAccessFields are an easy way to retrieve data from the web.
  * All requests you make will be cached, so if you request the same URL twice, it's no problem
    * WebAccessFields work the following way:
      * If there is a field marked with a ```W``` at the start of the line you can either:
      * put ONLY a get_return task as a valid WebAccessField (field = {"type": "get_return", "url": "blah"})
      * put a list of tasks to retrieve the wanted data
        * General task set-up:
        ```
        task = {
            type: task type as string (return, get_store, get_return, set_headers)
            
            Task specific fields:
            * set_headers:
                Set default headers to use while making requests for these WebAccessFields
                It is currently not possible to use the variables below.
                Please open an issue if you would like to use such feature.
            headers: {headers}
            
            * get_store:
                Get information from the web and store it into a variable.
                Use variable at any time using %variable_name%
            url: "url",
            path: {URIAccessField to retrieve the correct JSON data},
            destination: "destination_variable_name" (WITHOUT % at the start and end),
            headers: {optional}
            
            * return
                Return a compiled string
            value: "string to return"    
        
            * get_return:
                Get information from the web and return it (for example return newest build ID)
            url: "url",
            path: {URIAccessField to retrieve the correct JSON data},
            headers: {optional}
        }
      ```
      * If you only want to return a string (for example when you need to return the URL to download the newest artifact) you can just put a string as a valid WebAccessField
      e.g task = "www.url_with%variables%"

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
                  access: How to navigate to the version string (like in URIAccessField)
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

source: {
    server: The name of the API / server to download from in text (e.g: "paper API")
N   compatibility:
W       remote: WebAccessField to view compatible versions
            You may use %build% as the last buildID (will be out of date if check mode is "always")
            You may use %newest_version%, %newest_major% (1.x) and %newest_minor% (.x), they will represent the LAST compatible versions
        check: When to check for the newest compatibility
            possible settings:
            "always": always check for compatibility before checking for the newest build
                      this can be useful if the software uses "per-version" build IDs and
                      you need to "retrieve" the newest build for the newest version
            "build": check for new compatibility on recieving a new build
            
            if you DON't want to check for compatibility - remove the whole compatibility section        
            you can still use %newest_version%, it will then put in the newest version stored in software.json
        behaviour: How to handle an update to compatibility
            If the URL you pointed to in "remote" shows a new update, this setting will 
            decide what to to with the new data
            
            If the URL points to a ARRAY of compatible versions (e.g ["1.19", "1.19.1", "1.19.2"]):
                "all|minor": All versions in this array are compatible with the software ("1.19 - 1.19.2") ALERT: Wont include higher 1.19.2 versions
                "max|minor": Only the EXACT NEWESt version is compatible with the software (-> ONLY "1.19.2") 
                "all|major": All versions and minor versions of maximum version are compatible (would convert "1.6 - 1.8" to "1.6 - 1.8.99")
                "max|major": All minor versions for the maximum major versions are compatible (converts "1.17 - 1.17.1" to "1.17 - 1.17.99")
                "extend|major": Extend the previous up to the newest highest possible minimum version for the major version (useful for software that doesnt break on minor version updates)
                "extend|minor": Extend to the hightes exact version.
            If the URL points to a SINGLE compatible version (e.g "1.17")
                "precise|major": All minor versions for the major versions are supported: "1.17" > "1.17 - 1.17.99"
                "extend|major": Extend the previous compatibility to the all minor versions of this major version (compatible up to "1.17.99")
                "extend|minor": Extend the previous compatibility to the recieved version; "1.14 - 1.17.1" + "1.18" > "1.14 - 1.18"
                "precise|minor": Only support the recieved version.
    build: {
N       enabled: true / false

        You can use %newest_version%, it will be updated according to your "check" setting.

W       download: A WebAccessField pointing to the URL to download the latest buildID
W       remote: WebAccessField pointing to the newest build ID
            You can point to a list, the program will try to find the newest buildID (if buildID is convertable to int)
            If the newest buildID is always the last int in a list, please use -1 as the last URI access parameter (see URIAccessField)
        local: The local build ID. can be anything.
    }
    headers: headers that will be used while accessing this source. (compatibility and other things)
    tasks: {
N       enabled: Enable tasks to execute after downloading the newest build
        copy_downloaded: boolean; copy the downloaded file into tmp directory
        cleanup: boolean; clean up the files after an error (good for investigating errors)
        tasks: [
            {
N               enabled: wether task is enabled
                progress: {
                    value: What percentage to display in the progress bar (0 - 100) e.g 57
                    message: What message to display in the progress bar e.g "Patching vanilla server..."
                }
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
                    
                    * end
                        Requres the destination to the final file (like artifacts/plugin.jar)
                        The plugin will be copied to the main software folder.
                        Only avialible when updating software and not avialible while updating a server after version increment
                        
                    so value = e.g "artifacts/plugin.jar"
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
    newest_game_version: URIAccessField to retrieve the latest game version.
    version_check_interval: The interval (in days) between game version checks.
    git_auto_update: boolean; Try to automatically download newest version from git
    default_headers: The default header to use (dict)
    config_version: config version (int)
    max_progress_size: The maximum size (characters) a progress bar should use (except [] symbols); int
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
