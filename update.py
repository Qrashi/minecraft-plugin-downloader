import os
import sys
import traceback
from subprocess import run, PIPE

from utils.static_info import DAYS_SINCE_EPOCH
from utils.FileAccessField import FileAccessField
from utils.argparser import args
from utils.cli_provider import cli
from utils.errors import report
from utils.events import report as report_event
from utils.files import pool
from utils.software import Software
from utils.versions import Version


def main(check_all: bool, redownload: str):
    cli.load(f"Starting update, loading software data...", vanish=True)

    current_game_version = Version(pool.open("data/versions.json").json["current_version"])

    software_file = pool.open("data/software.json")
    servers = pool.open("data/servers.json")
    all_software = software_file.json
    config = pool.open("data/config.json").json
    cli.success("Loaded configurations...", vanish=True)

    if "config_version" not in config:
        config["config_version"] = 0
        for server_config in servers.json.values():
            if "auto_update" in server_config:
                server_config["auto_update"]["blocking"] = {}
        report_event("config", "Config version was increased to 0, blocking elements were RESET")
        cli.success("Fixed blocking lists - BLOCKING software has been reset")

    if "git_auto_update" not in config:
        config["git_auto_update"] = True
        report_event("git", "Automatic updates have been enabled!")
        cli.success("Activated automatic updates")

    if "default_header" not in config:
        config["default_header"] = {'User-Agent': 'Automated update script (github/Qrashi/minecraft-plugin-downloader)'}
        report_event("config", "Default header has been set.")
        cli.success("Set default header.")

    if config["git_auto_update"]:
        cli.info("Checking for git updates...", vanish=True)

        code = run("git fetch", stdout=PIPE, stderr=PIPE, shell=True)
        if code.returncode != 0:
            # Wrong return code
            cli.fail("Could not fetch git updates - code " + str(code.returncode))
            report(10, "Could not fetch git updates! code: " + str(code.returncode),
                   "Shell process returned non zero error code",
                   exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr))
        else:
            if not code.stdout.decode('utf-8').endswith(" "):
                # Update found
                cli.load("Downloading updates...", vanish=True)
            code = run("git pull", stdout=PIPE, stderr=PIPE, shell=True)
            if code.returncode != 0:
                cli.fail("Could not pull updates from git - code " + str(code.returncode))
                report(10, "Could not pull git updates! code: " + str(code.returncode),
                       "Shell process returned non zero error code",
                       exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr))
            else:
                if not code.stdout.decode('utf-8').endswith("up to date.\n"):
                    code = run("git log -n 1 --pretty=format:\"%H\"", stdout=PIPE, stderr=PIPE, shell=True)
                    if code.returncode != 0:
                        cli.fail(f"Could not get latest git version {code.returncode} - NON FATAL!")
                        report(1, f"Could not get last git version! code: {code.returncode}",
                               "Shell process returned non zero error code",
                               exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr))
                    else:
                        cli.success("Updated to commit " + code.stdout.decode('utf-8'))
                        report_event("git", "Updated all files to commit " + code.stdout.decode('utf-8'))
                    cli.warn("Restarting update script...")
                    os.execl(sys.executable, sys.executable, *sys.argv)

    software_objects = {}

    cli.info("Retrieving newest versions...", vanish=True)
    updated = 0
    check_redownload = not redownload == "none"
    for software in all_software:
        cli.load("Retrieving compatibility for " + software, vanish=True)
        obj = Software(software)  # Initialize every software
        was_updated = obj.retrieve_newest(
            check_all, (
                        check_redownload and obj.software == redownload))  # Retrieve the newest software, update hashes increment counter if successful
        updated = updated + 1 if was_updated else updated
        all_software[software]["hash"] = obj.hash
        software_objects[software] = obj

    cli.success("Retrieved newest versions!", vanish=True)
    # Update every server
    dependencies_updated = 0
    updated_servers = 0
    for server_name, server_info in servers.json.items():
        cli.info("Updating " + server_name, vanish=True)
        changed = False
        # Get the server version
        if server_info["version"]["type"] == "version":
            server_version = Version(server_info["version"]["value"])
        else:
            version_access = FileAccessField(server_info["version"]["value"])
            server_version = Version(version_access.access(pool.open(version_access.filepath).json))
        # game version detection for dependency
        if "auto_update" in server_info:
            # Check if server dependencies are ready
            # If an auto update is even required
            if server_info["auto_update"]["enabled"]:
                if not server_version.matches(current_game_version) and server_version.matches(
                        server_version.get_next_minor()):
                    for version in [server_version.get_next_minor(), current_game_version]:
                        server_info["auto_update"]["blocking"][version.string()] = {}
                        ready = True  # ready = ready for version increment
                        cli.info("Checking " + server_name + " version compatibility for " + version.string(),
                                 vanish=True)
                        for dependency in server_info["software"]:
                            if dependency not in all_software:
                                # >> Typo in config
                                cli.fail(
                                    "Error while updating " + server_name + " server: required software " + dependency + " not found in software register")
                                report(2, "updater - " + server_name,
                                       "Server has unknown dependency, server dependency file might have a typo!")
                                continue
                            software = software_objects[dependency]
                            if not version.fulfills(
                                    software.requirements):  # If there is no next minor, there IS no higher version -> the server is at MAX version which was ruled out above!
                                ready = False  # Plugin incompatibility found, abort
                                if dependency in server_info["auto_update"]["blocking"]:
                                    diff = DAYS_SINCE_EPOCH - \
                                           server_info["auto_update"]["blocking"][version.string()][dependency]["since"]
                                    if diff >= 3:
                                        report(int(min(max(2, 2 + (diff * 0.2)), 5)), "updater - " + server_name,
                                               "Server " + server_name + " is set to auto update, yet the dependency \"" + dependency + "\" has been blocking the automatic increment since " + str(
                                                   diff) + " days",
                                               additional="Server version: " + server_version.string() + " " + dependency + " version requirement: " + software.requirements.string())
                                else:
                                    server_info["auto_update"]["blocking"][version.string()][dependency] = DAYS_SINCE_EPOCH

                        if ready:  # Ready to version increment!
                            changed = True
                            if server_info["version"]["type"] == "version":  # Save version as string
                                servers.json[server_name]["version"]["value"] = version.string()
                            else:
                                version_access = FileAccessField(server_info["version"])
                                version_access.update(pool.open(version_access.filepath).json,
                                                      version.string())
                            server_info["auto_update"]["blocking"][version.string()] = {}
                            cli.success(
                                "Server " + server_name + " updated from " + server_version.string() + " to " + version.string())
                            report_event("updater - " + server_name,
                                         "Server version incremented to " + version.string())
            else:  # Version up to date
                server_info["auto_update"]["blocking"] = {}

        cli.info("Updating plugins for " + server_name, vanish=True)
        for dependency, info in server_info["software"].items():
            if dependency not in all_software:
                # >> Typo in config
                cli.fail(
                    "Error while updating " + server_name + " server: required software " + dependency + " not found in software register")
                report(2, "updater - " + server_name,
                       "Server has unknown dependency, server dependency file might have a typo!")
                continue
            else:
                software = software_objects[dependency]
                if software.needs_update(server_info["path"] + info["copy_path"]):  # Skip update if no update happened
                    if not server_info["software"][dependency]["enabled"]:
                        continue
                    if server_version.fulfills(software.requirements):
                        # Software IS compatible, copy is allowed > copy
                        software.copy(server_name)
                        changed = True
                        dependencies_updated = dependencies_updated + 1

        updated_servers = updated_servers + 1 if changed else updated_servers

    if updated != 0:
        cli.success("Detected and downloaded updates for " + str(updated) + " dependencies")
        cli.success("Updated " + str(dependencies_updated) + " dependencies in " + str(updated_servers) + " servers.")
    else:
        cli.success("Everything up to date!")

    pool.sync()
    cli.success("Update sequence complete")


if __name__ == "__main__":
    try:
        main(args.check_all_compatibility, args.redownload)
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        exit()
    except Exception as e:
        if not isinstance(e, KeyboardInterrupt):
            report(10, "updater - main", "Updater quit unexpectedly! Uncaught exception: ",
                   additional="Traceback: " + ''.join(traceback.format_exception(None, e, e.__traceback__)),
                   exception=e)
            cli.fail("ERROR: Uncaught exception: ")
            print(e)
            cli.fail("More detailed info can be found in the errors.json file")


else:
    cli.fail("This file needs to be executed directly!")
