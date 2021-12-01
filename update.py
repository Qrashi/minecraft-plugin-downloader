import traceback
from subprocess import run, PIPE

from utils import files
from utils.FileAccessField import FileAccessField
from utils.cli_provider import cli
from utils.error import report
from utils.events import report as report_event
from utils.file_pool import pool
from utils.info import DAYS_SINCE_EPOCH
from utils.software import Software
from utils.version import Version


def main():
    cli.load("Starting update, loading software data...", vanish=True)

    current_game_version = Version(pool.open("data/versions.json").json["current_version"])

    software_file = pool.open("data/software.json")
    servers = pool.open("data/servers.json")
    all_software = software_file.json
    config = pool.open("data/config.json").json
    cli.load("Downloading new software...", vanish=True)

    software_objects = {}

    cli.info("Retrieving newest versions...", vanish=True)
    updated = 0
    for software in all_software:
        cli.load("Retrieving compatibility for " + software, vanish=True)
        obj = Software(software)  # Initialize every software
        was_updated, new_hash = obj.retrieve_newest() # Retrieve the newest software, update hashes increment counter if successful
        updated = updated + 1 if was_updated else 0
        obj.hash = new_hash
        software_objects[software] = obj

    cli.success("Retrieved newest versions!", vanish=True)
    # Update every server
    dependencies_updated = 0
    updated_servers = 0
    for server_name, server_info in servers.json.items():
        changed = False
        # Get the server version
        if server_info["version"]["type"] == "version":
            server_version = Version(server_info["version"]["value"])
        else:
            access = FileAccessField(server_info["version"]["value"])
            server_version = Version(access.access(pool.open(access.filepath).json))
        # game version detection for dependency
        if "auto_update" in server_info:
            # Check if server dependencies are ready
            # If an auto update is even required
            if not server_version.matches(current_game_version):
                if server_info["auto_update"]["enabled"]:
                    cli.info("Checking " + server_name + " version compatibility", vanish=True)
                    ready = True  # ready = ready for version increment
                    for dependency in server_info["software"]:
                        if dependency not in all_software:
                            # >> Typo in config
                            cli.fail(
                                "Error while updating " + server_name + " server: required software " + dependency + " not found in software register")
                            report("updater - " + server_name, 2,
                                   "Server has unknown dependency, server dependency file might have a typo!")
                            continue
                        software = software_objects[dependency]
                        if not current_game_version.fulfills(
                                software.requirements) or server_version.get_next_minor().fulfills(
                                software.requirements):  # If there is no next minor, there IS no higher version -> the server is at MAX version which was ruled out above!
                            ready = False  # Plugin incompatibility found, abort
                            if dependency in server_info["auto_update"]["blocking"]:
                                diff = DAYS_SINCE_EPOCH - server_info["auto_update"]["blocking"][dependency][
                                    "since"]
                                if diff >= 3:
                                    report("updater - " + server_name, int(min(max(2, 2 + (diff * 0.2)), 5)),
                                           "Server " + server_name + " is set to auto update, yet the dependency \"" + dependency + "\" has been blocking the automatic increment since " + str(
                                               diff) + " days",
                                           additional="Server version: " + server_version.string() + " " + dependency + " version requirement: " + software.requirements.string())
                            else:
                                server_info["auto_update"]["blocking"].append(
                                    {"name": dependency, "since": DAYS_SINCE_EPOCH})

                    if ready:  # Ready to version increment!
                        changed = True
                        server_info["version"] = current_game_version.string()
                        server_info["auto_update"]["blocking"] = []
                        cli.success(
                            "Server " + server_name + " updated from " + server_version.string() + " to " + current_game_version.string())
                        report_event("updater - " + server_name,
                                     "Server version incremented to " + current_game_version.string())
            else:  # Version up to date
                server_info["auto_update"]["blocking"] = []

        for dependency, info in server_info["software"].items():
            if dependency not in all_software:
                # >> Typo in config
                cli.fail(
                    "Error while updating " + server_name + " server: required software " + dependency + " not found in software register")
                report("updater - " + server_name, 2,
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

        updated_servers = updated_servers + 1 if changed else 0

    cli.success("Detected and downloaded updates for " + str(updated) + " dependencies")
    cli.success("Updated " + str(dependencies_updated) + " dependencies in " + str(updated_servers) + " servers.")

    pool.sync()

    if config["git_auto_update"]:
        cli.info("Checking for git updates...", vanish=True)

        code = run("git fetch", stdout=PIPE, stderr=PIPE, shell=True)
        if code.returncode != 0:
            # Wrong return code
            cli.fail("Could not fetch git updates - code " + str(code.returncode))
            report("Could not fetch git updates! code: " + str(code.returncode),
                   exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr))
        else:
            code = run("git pull", stdout=PIPE, stderr=PIPE, shell=True)
            if code.returncode != 0:
                cli.fail("Could not pull updates from git - code " + str(code.returncode))
                report("Could not pull git updates! code: " + str(code.returncode),
                   exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr))
            else:
                cli.success("Updated git!")
                report_event("git", "Updated all files!")

    cli.success("Update sequence complete")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        exit()
    except Exception as e:
        if not isinstance(e, KeyboardInterrupt):
            report("updater - main", 10, "Updater quit unexpectedly! Uncaught exception: ", exception=e, additional="Traceback: " + ''.join(traceback.format_exception(None, e, e.__traceback__)))
            cli.fail("ERROR: Uncaught exception: ")
            print(e)
            cli.fail("More detailed info can be found in the errors.json file")


else:
    cli.fail("This file needs to be executed directly!")
