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
    cli.load("Downloading new software...", vanish=True)

    software_objects = {}

    cli.info("Retrieving newest versions...", vanish=True)
    for software in all_software:
        cli.load("Retrieving compatibility for " + software, vanish=True)
        obj = Software(software)  # Initialize every software
        obj.retrieve_newest()  # Retrieve the newest software
        software_objects[software] = obj

    cli.success("Retrieved newest versions!", vanish=True)
    # Update every server
    updated = 0
    for server_name, server_info in servers.json.items():
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
                        server_info["version"] = current_game_version.string()
                        server_info["auto_update"]["blocking"] = []
                        cli.success(
                            "Server " + server_name + " updated from " + server_version.string() + " to " + current_game_version.string())
                        report_event("updater - " + server_name,
                                     "Server version incremented to " + current_game_version.string())
            else:  # Version up to date
                server_info["auto_update"]["blocking"] = []

        for dependency in server_info["software"]:
            if dependency not in all_software:
                # >> Typo in config
                cli.fail(
                    "Error while updating " + server_name + " server: required software " + dependency + " not found in software register")
                report("updater - " + server_name, 2,
                       "Server has unknown dependency, server dependency file might have a typo!")
                continue
            else:
                software = software_objects[dependency]
                if software.needs_update():  # Skip update if no update happened
                    if not server_info["software"][dependency]["enabled"]:
                        continue
                    if server_version.fulfills(software.requirements):
                        # Software IS compatible, copy is allowed > copy
                        software.copy(server_name)
                        updated = updated + 1

    for software in software_objects.values():
        all_software[software.software]["hash"] = software.get_hash()
    if updated == 0:
        cli.success("Checked for new versions")
    else:
        cli.success("Updated " + str(updated) + " dependencies")

    pool.sync()
    cli.success("Update sequence complete")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        exit()
else:
    cli.fail("This file needs to be executed directly!")
