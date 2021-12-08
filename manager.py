import os

from utils.cli import CLIApp
from utils.files import pool
from utils.versions import is_valid, Version, VersionRangeRequirement


def main():
    cli.say("Starting, scanning software directory...")

    all_software = pool.open("data/software.json").json

    software_file_list = []
    for software in all_software.values():
        software_file_list.append(software["file"])

    detected_files = {}
    files = []
    with os.scandir(pool.open("data/config.json").json["sources_folder"]) as directory:
        for file in directory:
            if not file.name.endswith(".tmp"):
                files.append(file.name)

    for file in files:
        if file not in software_file_list:
            detected_files[file] = "added"

    for file in software_file_list:
        if file not in files:
            detected_files[file] = "removed"

    if len(detected_files) == 0:
        cli.fail("Scan complete, could not find any new / deleted files!")
        cli.say("Please put / remove the new software into the software folder!")
        exit()

    cli.success("Found " + str(len(detected_files)) + " changed files.")
    if len(detected_files) == 1:
        # We already know which software to select
        file = list(detected_files)[0]
        operation = detected_files[file]
    else:
        cli.say("Detected multiple new files. Please choose from the list: ")
        for detected_file, operation in detected_files.items():
            print("- " + detected_file + " (" + operation + ")")

        def ask():
            result = cli.ask("Software to manage: ", vanish=True)
            if result in detected_files.keys():
                return result
            else:
                cli.fail("This item is not on the list! Try again.", vanish=True)
                return ask()

        file = ask()
        operation = detected_files[file]

    if operation == "added":
        add(file)
    else:
        remove(file)


def remove(file: str):
    software_file = pool.open("data/software.json")
    sources_file = pool.open("data/sources.json")
    all_software = software_file.json

    cli.update_sender("RM")
    cli.success("Removing " + file + " from the software repository...")

    name = ""
    software_info = {}
    for name, software in all_software.items():
        if software["file"] == file:
            software_info = software
            break

    rm_files = cli.ask("Would you like do delete all registered occurrences of this dependency? (Copies of the "
                       "dependency in a server) ") in ["y", "yes"]
    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
    cli.update_sender("SUM")
    cli.info("Summary")
    cli.say("To remove: ")
    cli.say(
        "dependency \"" + software_info["identifier"] + "\" (" + name + ") [" + str(
            software_info["severity"]) + "]")
    cli.say("local file: " + file)
    cli.say("Version requirements: " + VersionRangeRequirement(software_info["requirements"]).string())
    if name in sources_file.json:
        cli.say(name + "'s auto-update configuration")
    if rm_files:
        cli.say("ALL LOCAL COPIED DEPENDENCIES (in all servers!)")

    if cli.ask("Please confirm operation: (yes / no) ").lower() not in ["y", "yes"]:
        cli.fail("Aborting")
        exit()

    servers_file = pool.open("data/servers.json")

    if rm_files:
        servers_rm = []
        servers = servers_file.json
        for server_name, server in servers.items():
            if name in server["software"]:
                path = server["path"] + "/" + server["software"][name]["copy_path"]
                cli.simple_wait_fixed_time("Deleting " + path + "...", "Deleted", 1)
                os.remove(path)
                servers_rm.append(server_name)
        for server in servers_rm:
            servers[server]["software"].pop(name)
        servers_file.json = servers
        cli.info("Deleted ALL files and ALL occurrences in server configurations!")

    if name in sources_file.json:
        sources_file.json.pop(name)
    all_software.pop(name)
    software_file.json = all_software

    cli.info("Software configurations removed!")
    pool.sync()


def add(file: str):
    software_file = pool.open("data/software.json")
    all_software = software_file.json

    cli.update_sender("ADD")
    cli.success("Adding " + file + " to the software repository...")  # Doesn't actually do something

    def ask():
        result = cli.ask("Please enter the name of the software (e.g waterfall): ", vanish=True)
        if result in all_software:
            cli.fail("This software already exists! Try again.")
            return ask()
        return result

    name = ask()

    identifier = cli.ask("Please enter a human understandable identifier for your software (e.g Proxy / Waterfall): ", vanish=True)

    def ask():
        result = cli.ask("How severe would any error related to this software be? (0-10): ", vanish=True)
        if result.isdigit():
            result = int(result)
            if 0 <= result <= 10:
                return int(result)

        cli.say("Please enter a number between 0 and 10")
        return ask()

    severity = ask()

    cli.update_sender("VER")

    def ask(version: str) -> Version:
        version = cli.ask("Please enter " + version + " version (e.g: 1.17.1): ", vanish=True)
        if is_valid(version):
            return Version(version)
        cli.fail("This is not a valid version! ")
        return ask(version)

    cli.say("Please define the range of compatible versions (includes the entered version)")
    minimum = ask("oldest compatible")
    maximum = ask("newest compatible")
    range_requirement = VersionRangeRequirement((minimum, maximum))

    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
    cli.info("If you would like to add auto-update, please read \"examples.md\"!")

    cli.success("All data collected!")
    cli.say("To add: ")
    cli.say("Adding new dependency: " + identifier + " (" + name + ") [" + str(severity) + "]")
    cli.say("local file: " + file)
    cli.say("Version requirements: " + range_requirement.string())

    if cli.ask("Is that ok? ").lower() not in ["y", "yes"]:
        if cli.ask("Are you sure you would like to cancel (n, no to \"cancel cancel\") ").lower() not in ["n", "no",
                                                                                                          ""]:
            cli.fail("Aborting")
            exit()

    cli.update_sender("MNG")
    cli.info("Saving to json...")

    sources_file = pool.open("data/sources.json")

    all_software[name] = {
        "file": file,
        "hash": "",
        "identifier": identifier,
        "requirements": range_requirement.dict(),
        "severity": severity,
    }

    software_file.json = all_software
    pool.sync()
    cli.info("If you would like to add auto-update, please read \"examples.md\"!")


if __name__ != "__main__":
    print("This file is only meant to be executed from the console")
    exit()
else:
    cli = CLIApp("INI")
    try:
        main()
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        exit()
