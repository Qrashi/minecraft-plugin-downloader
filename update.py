import os
import sys
import traceback
from subprocess import run, PIPE
from time import sleep

from utils.static_info import DAYS_SINCE_EPOCH
from utils.argparser import args
from utils.cli_provider import cli
from utils.access_fields import FileAccessField
from utils.errors import report
from utils.events import report as report_event
from utils.files import pool
from utils.software import Software
from utils.versions import Version, check_game_versions
from utils.dict_utils import enabled
from utils.tasks import execute
from utils.context_manager import context
from utils.file_defaults import CONFIG


def main(check_all: bool, re_download: str):
    context.software = "main"
    context.failure_severity = 10
    context.task = "loading configurations"
    if check_all:
        cli.info("Checking compatibility for every software")
    cli.load(f"Starting update, loading software data...", vanish=True)

    check_game_versions()
    current_game_version = Version(pool.open("data/versions.json").json["current_version"])

    software_file = pool.open("data/software.json", default="{}")
    servers = pool.open("data/servers.json", default="{}")
    all_software = software_file.json
    config = pool.open("data/config.json", default=CONFIG).json
    cli.success("Loaded configurations...", vanish=True)

    context.task = "updating configurations"
    if "config_version" not in config:
        if config["config_version"] < 1:
            cli.fail("A lot of breaking changes have been introduced since the last update.")
            cli.info("Please update all URLAccessFields to the new WebAccessFields")
            cli.info("When you are done, set the config_version in the config to 1.")
            cli.fail("Until then, you will not be able to use this program.")
            cli.info("You may delete your current config to generate a new (valid) one.")
            sys.exit()

    context.task = "checking for git-updates"
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

    context.task = "checking for new software updates"
    progress = cli.progress_bar("Checking for newest versions...", vanish=True)
    checked = 0
    total_software = len(all_software)
    updated = 0
    check_re_download = not re_download == "none"
    for software in all_software:
        checked = checked + 1
        progress.update_message("Checking " + software + "...", (checked / total_software) * 100)
        obj = Software(software)  # Initialize every software
        was_updated = obj.retrieve_newest(
            check_all, (
                    check_re_download and obj.software == re_download))  # Retrieve the newest software, update hashes increment counter if successful
        updated = updated + 1 if was_updated else updated
        all_software[software]["hash"] = obj.hash
        software_objects[software] = obj

    progress.complete("Checked " + str(total_software) + " times for updates")
    # Update every server
    servers_total = len(servers.json)
    servers_iter = 0
    dependencies_updated = 0
    updated_servers = 0
    progress = cli.progress_bar("Checking servers for updates")
    for server_name, server_info in servers.json.items():
        servers_iter = servers_iter + 1
        context.software = server_name
        context.failure_severity = 10
        context.task = "getting information"
        progress.update_message("Updating " + server_name, (servers_iter / servers_total) * 100)
        sleep(0.05)
        changed = False
        # Get the server version
        if server_info["version"]["type"] == "version":
            server_version = Version(server_info["version"]["value"])
        else:
            version_access = FileAccessField(server_info["version"]["value"])
            server_version = Version(version_access.access())
        # game version detection for dependency
        if "auto_update" in server_info:
            context.failure_severity = 5
            context.task = "auto-updating server, getting eligible versions"
            # Check if server dependencies are ready
            # If an auto update is even required
            if server_info["auto_update"]["enabled"]:
                if not server_version.matches(current_game_version):
                    # Possibly out of date
                    version_iter = server_version
                    higher_versions = []
                    while not version_iter.matches(current_game_version):
                        version_iter = version_iter.get_next_minor()
                        higher_versions.append(version_iter)
                    for version in higher_versions:
                        context.task = "auto-updating server, checking " + version.string()
                        if not version.string() in server_info["auto_update"]["blocking"]:
                            server_info["auto_update"]["blocking"][version.string()] = {}
                        ready = True  # ready = ready for version increment
                        failing = 0
                        progress.update_message("Checking " + server_name + " version compatibility for " + version.string(), 0)
                        dep_iter = 0
                        dependencies_total = len(server_info["software"])
                        for dependency in server_info["software"]:
                            progress.update((dep_iter / dependencies_total) * 100)
                            if not server_info["software"][dependency]["enabled"]:
                                if dependency in server_info["auto_update"]["blocking"][version.string()]:
                                    server_info["auto_update"]["blocking"][version.string()].pop(dependency)
                                continue
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
                                failing = failing + 1
                                if dependency in server_info["auto_update"]["blocking"][version.string()]:
                                    diff = DAYS_SINCE_EPOCH - \
                                           server_info["auto_update"]["blocking"][version.string()][dependency]
                                    if diff >= 3:
                                        report(int(min(max(2, 2 + (diff * 0.2)), 5)), "updater - " + server_name,
                                               "Server " + server_name + " is set to auto update, yet the dependency \"" + dependency + "\" has been blocking the automatic increment for " + str(
                                                   diff) + " days",
                                               additional="Server version: " + server_version.string() + " " + dependency + " version requirement: " + software.requirements.string())
                                else:
                                    server_info["auto_update"]["blocking"][version.string()][
                                        dependency] = DAYS_SINCE_EPOCH

                            else:
                                if dependency in server_info["auto_update"]["blocking"][version.string()]:
                                    server_info["auto_update"]["blocking"][version.string()].pop(dependency)

                        if ready:  # Ready to version increment!
                            context.task = "server eligible for update!"
                            if server_version.is_higher(version):
                                # Don't "downgrade" or "upgrade" to the "same version" (current game version can be in the pool twice)
                                server_info["auto_update"]["blocking"].pop(version.string())
                                continue
                            changed = True
                            if server_info["version"]["type"] == "version":  # Save version as string
                                server_info[server_name]["version"]["value"] = version.string()
                            else:
                                version_access = FileAccessField(server_info["version"])
                                version_access.update(version.string())
                            server_info["auto_update"]["blocking"].pop(version.string())
                            progress.update_message(
                                "Updating " + server_name + " from " + server_version.string() + " to " + version.string(), 0)
                            update = True
                            if "on_update" in server_info["auto_update"]:
                                # Execute tasks
                                context.failure_severity = 8
                                context.software = server_name
                                context.task = "updating server to " + version.string()
                                for task in server_info["auto_update"]["on_update"]:
                                    if enabled(task):
                                        progress.update_message(task["progress"]["message"], done=task["progress"]["value"])
                                        if not execute(task, server_info["path"], {"%old_version%": server_version.string(), "%new_version%": version.string()}):
                                            # Error while executing task
                                            update = False
                                            progress.fail("Could not update " + server_name + " to " + version.string() + ". See errors.json")
                                            report(8, "update of " + server_name, "could not execute all update tasks. some things may need to be cleaned up.", additional="script doesn't clean up automatically.")
                                            break
                            if update:
                                server_version = version
                                report_event("updater - " + server_name,
                                             "Server updated to " + version.string())
                                progress.complete("Updated " + server_name + " to " + version.string() + "!")

                        else:
                            progress.fail(server_name + " not compatible with " + version.string() + "(" + str(failing) + " non-compatible)")

                else:  # Version up to date
                    server_info["auto_update"]["blocking"] = {}

        progress.update_message(f"updating {server_name} dependencies", (servers_iter / servers_total) * 100)
        context.failure_severity = 8
        context.software = server_name
        context.task = "updating dependencies"
        dep_total = len(server_info["software"])
        dep_iter = 0
        for dependency, info in server_info["software"].items():
            sleep(0.01)
            progress.update((dep_iter / dep_total) * 100)
            if dependency not in all_software:
                # >> Typo in config
                cli.fail(
                    "Error while updating " + server_name + " server: required software " + dependency + " not found in software register")
                report(8, "updater - " + server_name,
                       "Server has unknown dependency, server dependency file might have a typo!")
                continue
            software = software_objects[dependency]
            context.task = "updating " + dependency
            if not server_info["software"][dependency]["enabled"]:
                continue
            if software.needs_update(server_info["path"] + info["copy_path"]):  # Skip update if no update happened
                if server_version.fulfills(software.requirements):
                    # Software IS compatible, copy is allowed > copy
                    software.copy(server_name)
                    context.task = "copying " + dependency
                    changed = True
                    dependencies_updated = dependencies_updated + 1

        updated_servers = updated_servers + 1 if changed else updated_servers
        servers.json[server_name] = server_info

    context.failure_severity = 10
    context.task = "finalizing"
    context.software = "main"
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
        sys.exit()
    except Exception as e:
        if not isinstance(e, KeyboardInterrupt):
            report(context.failure_severity, "updater - main", f"Updater quit unexpectedly! {context.software} - {context.task}",
                   additional="Traceback: " + ''.join(traceback.format_exception(None, e, e.__traceback__)),
                   exception=e)
            cli.fail("ERROR: Uncaught exception: ")
            print(e)
            cli.fail("More detailed info can be found in the errors.json file")


else:
    cli.fail("This file needs to be executed directly!")
