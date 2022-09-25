import os
import sys
import traceback
from subprocess import run, PIPE
from typing import Dict

from singlejson import load, sync

import utils.cli as cli
from utils.access_fields import FileAccessField
from utils.argparser import args
from utils.context_manager import context
from utils.dict_utils import enabled
from utils.errors import report
from utils.events import report as report_event
from utils.file_defaults import CONFIG
from utils.software import Software
from utils.static_info import DAYS_SINCE_EPOCH
from utils.tasks import execute
from utils.versions import Version, check_game_versions


def main(check_all_compatibility: bool, re_download: str, skip_dependency_check: bool):
    """
    Execute the main update.
    :param check_all_compatibility: Weather to check all software for updates
    :param re_download: Weather to re-download a specific software
    :param skip_dependency_check: Skip checking for new dependencies
    :return:
    """
    context.name = "main"
    context.failure_severity = 10
    context.task = "loading configurations"

    cli.update_sender("INI")
    cli.loading("Starting update, loading game version data...", vanish=True)
    check_game_versions()
    current_game_version = Version(load("data/versions.json").json["current_version"])

    if check_all_compatibility:
        cli.info("Checking compatibility for every software!")

    software_file = load("data/software.json", default="{}")
    servers = load("data/servers.json", default="{}")
    all_software = software_file.json
    config = load("data/config.json", default=CONFIG).json

    context.task = "updating configurations"
    if "config_version" not in config and config["config_version"] < 1:
        cli.fail("A lot of breaking changes have been introduced since the last update.")
        cli.info("Please update all URLAccessFields to the new WebAccessFields")
        cli.info("When you are done, set the config_version in the config to 1.")
        cli.fail("Until then, you will not be able to use this program.")
        cli.info("You may delete your current config to generate a new (valid) one.")
        sys.exit()

    context.task = "checking for git-updates"
    if config["git_auto_update"]:
        cli.update_sender("GIT")
        cli.info("Checking for git updates [1/2]", vanish=True)

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
                cli.loading("Downloading updates [2/2]", vanish=True)
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
                    cli.warn("Restarting update script!")
                    os.execl(sys.executable, sys.executable, *sys.argv)

    # Update software (fetch sources)
    context.task = "checking for new software updates"
    cli.update_sender("SFW")
    check_re_download = not re_download == "none"
    progress = cli.progress_bar("Checking for newest versions...")

    total_software = len(all_software)
    checked = updated = 0
    software_objects: Dict[str, Software] = {}

    for software_name, software_data in all_software.items():
        checked = checked + 1
        progress.update_message(f"Checking {software_name}...", done=(checked / total_software) * 100)
        software = Software(software_data, software_name)
        if skip_dependency_check:
            was_updated = False
        else:
            was_updated = software.retrieve_newest(check_all_compatibility, (check_re_download and software.name == re_download))
        updated = updated + 1 if was_updated else updated
        software_data["hash"] = software.hash
        software_objects[software_name] = software

    if updated == 0:
        progress.complete(f"Checked for {total_software} software updates")
    else:
        progress.complete(f"Found {updated} updates, checked {total_software}")

    # Update servers
    cli.update_sender("SRV")
    servers_total = len(servers.json)
    servers_iter = 0
    dependencies_updated = 0
    updated_servers = 0
    progress = cli.progress_bar("Checking servers for updates")
    for server_name, server_info in servers.json.items():
        servers_iter = servers_iter + 1
        context.name = server_name
        context.failure_severity = 10
        context.task = "getting information"
        prog = (servers_iter / servers_total) * 100
        progress.update_message("Updating " + server_name, prog)
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
                        progress.update_message(
                            "Checking " + server_name + " version compatibility for " + version.string())
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
                                "Updating " + server_name + " from " + server_version.string() + " to " + version.string())
                            update = True
                            if "on_update" in server_info["auto_update"]:
                                # Execute tasks
                                context.failure_severity = 8
                                context.name = server_name
                                context.task = "updating server to " + version.string()
                                for task in server_info["auto_update"]["on_update"]:
                                    if enabled(task):
                                        progress.update_message(task["progress"]["message"],
                                                                done=task["progress"]["value"])
                                        if not execute(task, server_info["path"],
                                                       {"%old_version%": server_version.string(),
                                                        "%new_version%": version.string()}):
                                            # Error while executing task
                                            update = False
                                            progress.fail(
                                                "Could not update " + server_name + " to " + version.string() + ". See errors.json")
                                            report(8, "update of " + server_name,
                                                   "could not execute all update tasks. some things may need to be cleaned up.",
                                                   additional="script doesn't clean up automatically.")
                                            break
                            if update:
                                server_version = version
                                report_event("updater - " + server_name,
                                             "Server updated to " + version.string())
                                progress.complete("Updated " + server_name + " to " + version.string() + "!")

                        else:
                            progress.fail(server_name + " not compatible with " + version.string() + "(" + str(
                                failing) + " non-compatible)")

                else:  # Version up to date
                    server_info["auto_update"]["blocking"] = {}

        context.failure_severity = 8
        context.name = server_name
        context.task = "updating dependencies"
        dependencies_total = len(server_info["software"])
        dep_iter = 0
        progress.update_message(f"Checking {server_name} dependencies [{dep_iter}/{dependencies_total}]", done=prog)
        for dependency, info in server_info["software"].items():
            dep_iter = dep_iter + 1
            progress.update_message(f"Checking {server_name} dependencies [{dep_iter}/{dependencies_total}]")
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
            if software.needs_update(server_info["path"] + info["copy_path"]) and server_version.fulfills(
                    software.requirements):
                # Skip update if no update happened
                # Software IS compatible, copy is allowed > copy
                context.task = "copying " + dependency
                progress.update_message(f"Updating {server_name} dependencies - {dependency}")
                software.copy(server_name, f"[{dep_iter}/{dependencies_total}]")
                changed = True
                dependencies_updated = dependencies_updated + 1

        updated_servers = updated_servers + 1 if changed else updated_servers
        servers.json[server_name] = server_info

    context.failure_severity = 10
    context.task = "finalizing"
    context.name = "main"
    if updated != 0:
        progress.complete(f"Updated {dependencies_updated} dependencies in {updated_servers} servers.")
    else:
        progress.complete(f"Checked {len(servers.json)} servers for updates.")

    cli.update_sender("END")
    cli.simple_wait_fixed_time("Saving data to disk...", "Data saved!", 1.5, green=True)
    sync()


if __name__ == "__main__":
    try:
        main(args.check_all_compatibility, args.redownload, args.skip_dependency_check)
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        sys.exit()
    except Exception as e:
        if not isinstance(e, KeyboardInterrupt):
            report(context.failure_severity, "updater - main",
                   f"Updater quit unexpectedly! {context.name} - {context.task}",
                   additional="Traceback: " + ''.join(traceback.format_exception(None, e, e.__traceback__)),
                   exception=e)
            cli.fail("ERROR: Uncaught exception: ")
            print(e)
            cli.fail("More detailed info can be found in the errors.json file")


else:
    cli.fail("This file needs to be executed directly!")
