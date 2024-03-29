import os
import sys
from time import sleep

import utils.cli as cli
from utils.file_defaults import CONFIG
from singlejson import load, sync
from utils.versions import is_valid, Version, VersionRangeRequirement
from utils.context_manager import context
from utils.sha244 import get_hash


def main():
    """
    Run the main management program
    :return:
    """
    context.task = "managing dependencies"
    context.failure_severity = 9
    context.name = "manager"
    cli.update_sender("MAN")
    cli.say("Starting, scanning software directory...")

    all_software = load("data/software.json", default="{}").json
    config = load("data/config.json", default=CONFIG).json

    software_file_list = {}
    for software, info in all_software.items():
        software_file_list[info["file"]] = software

    detected_files = {}
    files = []
    with os.scandir(config["sources_folder"]) as directory:
        for file in directory:
            if not file.name.endswith(".tmp"):
                files.append(file.name)
            if file in software_file_list:
                if get_hash(config["sources_folder"] + "/" + file) != all_software[software_file_list[file]]["hash"]:
                    detected_files[file] = "changed"

    for file in files:
        if file not in software_file_list:
            detected_files[file] = "added"

    for file in software_file_list:
        if file not in files:
            detected_files[file] = "removed"

    if len(detected_files) == 0:
        cli.success("Scan complete, could not find any new / deleted / changed files!")
        cli.warn("You may now select software to change:")
        for file in software_file_list:
            detected_files[file] = "change information"

    if len(detected_files) == 1:
        # We already know which software to select
        file = list(detected_files)[0]
        operation = detected_files[file]
    else:
        cli.warn("Please choose which file / software to edit:")
        for detected_file, operation in detected_files.items():
            print("- " + detected_file + " (" + operation + ")")

        def ask():
            result = cli.ask("Software to manage: ", vanish=True)
            if result in detected_files:
                return result
            cli.fail("This item is not on the list! Try again.", vanish=True)
            return ask()

        file = ask()
        operation = detected_files[file]

    if operation == "added":
        add(file)
    elif operation == "removed":
        remove(file)
    else:
        change(file, software_file_list[file])


def change(file: str, software: str):
    """
    Change software information
    :param file: File to change
    :param software: software identifier of software to change
    :return:
    """
    software_file = load("data/software.json", default="{}")

    cli.info("Selected " + file + ".")

    def ask_action():
        print("\n" * 30)
        cli.info("COMPATIBILITY - change compatibility (" + VersionRangeRequirement(software_file.json[software]["requirements"]).short_string() + ")")
        cli.info(f"SEVERITY - change severity")
        cli.info("IDENTIFIER - change identifier")
        cli.info("SAVE - save file")
        res = cli.ask("Specify action: ")
        if res == "COMPATIBILITY":
            cli.info("Setting new compatibility.")
            cli.info("Current compatibility: " + VersionRangeRequirement(software_file.json[software]["requirements"]).short_string())

            def ask_compatibility(version: str) -> Version:
                """
                Ask for new compatible version
                :param version: version (lowest, highest)
                :return: A Version
                """
                ver = cli.ask(f"Enter {version} version: ")
                if is_valid(ver):
                    return Version(ver)
                else:
                    cli.fail(version + " is not a valid version!")
                    return ask_compatibility(version)

            oldest = ask_compatibility("oldest compatible")
            newest = ask_compatibility("newest compatible")
            new_compat = VersionRangeRequirement((oldest, newest))
            software_file.json[software]["requirements"] = new_compat.dict()
            cli.info("New software " + new_compat.string())
            ask_action()
        elif res == "SEVERITY":
            cli.info("Setting new severity.")
            cli.info("Current severity: " + str(software_file.json[software]["severity"]))

            def ask_severity() -> int:
                """
                Ask for new severity
                :return:
                """
                new_severity = cli.ask("Enter new severity: ")
                if new_severity.isdigit():
                    new_severity = int(new_severity)
                    if 0 <= new_severity <= 10:
                        return new_severity

                cli.fail("Please enter a number between 0 and 10!")
                return ask_severity()

            severity = ask_severity()
            software_file.json[software]["severity"] = severity
            cli.info("New severity: " + str(severity))
            ask_action()
        elif res == "IDENTIFIER":
            cli.info("Setting new identifier.")
            cli.info("Current identifier: " + str(software_file.json[software]["identifier"]))
            new_identifier = cli.ask("Please enter new identifier: ")
            software_file.json[software]["identifier"] = new_identifier
            cli.info("New identifier: " + new_identifier)
            ask_action()
        else:
            cli.simple_wait_fixed_time("Saving changes... (CRTL-C to abort)", "Saved!", 3, green=True)
            sync()

    ask_action()


def remove(file: str):
    """
    Remove software from the software pool
    :param file: file to remove
    :return:
    """
    software_file = load("data/software.json", default="{}")
    sources = load("data/sources.json", default="{}")
    software = software_file.json
    servers = load("data/servers.json").json

    cli.update_sender("RM")
    cli.success("Removing " + file + " from the software repository...")

    found = name = software_info = False
    for name, software_info in software.items():
        if software_info["file"] == file:
            found = True
            break

    if not found:
        cli.fail("Could not find software in software register.")
        sys.exit()

    to_remove = []
    for server_name, info in servers.items():
        if name in info["software"]:
            to_remove.append([info["path"] + info["software"][name]["copy_path"], server_name])

    rm_files = cli.ask(f"Would you like to delete all {len(to_remove)} occurrences?") in ["y", "yes"]
    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
    cli.update_sender("SUM")
    cli.info("Summary")
    cli.say("To remove: ")
    cli.say("dependency \"" + software_info["identifier"] + f"\" ({name}) [" + str(software_info["severity"]) + "]")
    cli.say("local file: " + file)
    if name in sources.json:
        cli.info(f"{name}'s auto-update configuration")
    if rm_files:
        cli.warn("ALL LOCAL COPIED DEPENDENCIES (in all servers!)")

    if cli.ask("Please confirm operation: (yes / no) ").lower() not in ["y", "yes"]:
        cli.fail("Aborting")
        sys.exit()

    if rm_files:
        progress = cli.progress_bar("Deleting occurrences...")
        total = len(to_remove)
        index = 0
        for rm in to_remove:
            index = index + 1
            progress.update_message(f"Deleting in server {rm[1]}", (index / total) * 100)
            sleep(1)
            os.remove(rm[0])
            servers[rm[1]]["software"].pop(name)
        progress.complete("Deleted all occurrences in servers")

    if name in sources.json:
        sources.json.pop(name)
    software.pop(name)
    software_file.json = software

    cli.simple_wait_fixed_time("Saving data... (CRTL-C to cancel)", "Data saved!", 5)
    sync()


def add(file: str):
    """
    Add software to the pool
    :param file: file to add
    :return:
    """
    software_file = load("data/software.json", default="{}")
    all_software = software_file.json

    cli.update_sender("ADD")
    cli.info(f"Adding {file} to the software repository...")

    def ask_name():
        """
        Ask for the name of the software
        :return:
        """
        if file.find('.') == -1:  # No . found
            default = file
        else:
            default = file[:file.find('.')]
        result = cli.ask(f"Enter name (default: {default}): ", vanish=True)
        if result in all_software:
            cli.fail("This name already exists! Try again.")
            return ask_name()
        if result == "":
            return default
        return result

    name = ask_name()

    identifier = cli.ask("Enter a short description (e.g waterfall / proxy)", vanish=True)

    def ask_severity():
        """
        Ask for severity of software
        :return:
        """
        result = cli.ask("Enter error severity (0-10): ", vanish=True)
        if result.isdigit():
            result = int(result)
            if 0 <= result <= 10:
                return int(result)

        cli.say("Please enter a number between 0 and 10")
        return ask_severity()

    severity = ask_severity()

    cli.update_sender("VER")

    def ask_version(version: str) -> Version:
        """
        Ask for a specific version (e.g oldest or newest)
        :param version: version to ask for
        :return: valid version object
        """
        version = cli.ask("Please enter " + version + " version (e.g: 1.17.1): ")
        if is_valid(version):
            return Version(version)
        cli.fail(f"{version} is not a valid version!")
        return ask_version(version)

    cli.info("Define the range of compatible versions (includes the entered version)")
    minimum = ask_version("oldest compatible")
    maximum = ask_version("newest compatible")
    range_requirement = VersionRangeRequirement((minimum, maximum))

    print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")

    cli.success("All data collected!")
    cli.info("To add: ")
    cli.info("Adding new dependency: " + identifier + " (" + name + ") [" + str(severity) + "]")
    cli.info("local file: " + file)
    cli.info("Version requirements: " + range_requirement.string())
    cli.warn("If you would like to add auto-update, please read \"examples.md\"!")

    if cli.ask("Add to register? ").lower() not in ["y", "yes"] and \
            cli.ask("Confirm cancel (n, no to \"cancel cancel\") ").lower() not in ["n", "no", ""]:
        cli.fail("Aborting")
        sys.exit()

    all_software[name] = {
        "file": file,
        "hash": get_hash(file),
        "identifier": identifier,
        "requirements": range_requirement.dict(),
        "severity": severity,
    }

    software_file.json = all_software
    cli.simple_wait_fixed_time("Saving data...", "Data saved!", 1.5, green=True)
    sync()


if __name__ != "__main__":
    print("This file is only meant to be executed from the console")
    sys.exit()
else:
    try:
        main()
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        sys.exit()
