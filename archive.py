import argparse
import datetime
import sys

import utils.cli as cli
from singlejson import JSONFile


def get_time(timestamp: int) -> str:
    """
    Get a formatted time from a timestamp
    :param timestamp: timestamp to get time from
    :return: formatted time
    """
    return datetime.datetime.fromtimestamp(timestamp).strftime("%d.%m.%y at %H:%M")


def main(silent: bool):
    """
    Manage archives
    :param silent: silent mode (run without user input)
    :return:
    """
    cli.update_sender("ARM")
    cli.loading("Accessing archive database & current errors", vanish=True)
    errors_file, events_file = JSONFile("data/errors.json", default="[]"), JSONFile("data/events.json")
    archive_info = JSONFile("data/archive/archive.json",
                            default=str({"last": 0, "total": {"errors": 0, "events": 0}, "archives": []}).replace("\'",
                                                                                                                  "\""))
    last = archive_info.json["last"]
    if datetime.datetime.now().timestamp() - last < 70:
        cli.fail("You may only create an archive every 70 seconds in order to")
        cli.fail("prevent directories with the same name from being generated.")
        cli.info(f"Please wait {70 - int(datetime.datetime.now().timestamp()) - last} seconds and retry.")
        sys.exit()
    if len(events_file.json) == 0 and len(errors_file.json) == 0:
        cli.fail("Nothing to archive!")
        sys.exit()

    if silent:
        archive(last, int(datetime.datetime.now().timestamp()), silent)
        cli.success("Archive complete!")
        sys.exit()
    cli.info(f"Preparing to archive {len(errors_file.json)} errors & {len(events_file.json)} events.")
    if cli.ask("Is this okay? (yes/y) ").lower() in ["y", "yes"]:
        archive(last, int(datetime.datetime.now().timestamp()), silent)
        cli.success("Archive complete!")
    else:
        cli.fail("Aborting!")
        sys.exit()


def archive(start: int, end: int, silent: bool):
    """
    Archive errors
    :param start: first entry in archive
    :param end: end of archive
    :param silent: run in silent (non-interactive) mode
    :return:
    """
    dir_name = f"archive from {get_time(start)} to {get_time(end)}"
    if not silent:
        new_name = cli.ask("Please enter archive name (blank for default): ")
        if new_name != "":
            dir_name = new_name

    archive_data, archived_errors, archived_events = JSONFile(f"data/archive/{dir_name}/data.json"), JSONFile(
        f"data/archive/{dir_name}/errors.json"), JSONFile(f"data/archive/{dir_name}/events.json")
    errors, events = JSONFile("data/errors.json", default="[]"), JSONFile("data/events.json", default="[]")
    archives_info = JSONFile("data/archive/archive.json")
    nr_errors, nr_events = len(errors.json), len(events.json)
    archive_data.json = {
        "timeframe": {
            "start": start,
            "end": end
        },
        "stats": {
            "errors": nr_errors,
            "events": nr_events
        }
    }
    archived_errors.json = errors.json
    archived_events.json = events.json
    if not silent:
        cli.simple_wait_fixed_time("Saving to archive...", "Saved to archive!", 3, vanish=True, green=True)
    archived_errors.save()
    archived_events.save()
    archive_data.save()
    errors.json = []
    events.json = []
    archives_info.json["last"] = end
    archives_info.json["total"]["errors"] = archives_info.json["total"]["errors"] + nr_errors
    archives_info.json["total"]["events"] = archives_info.json["total"]["events"] + nr_events
    archives_info.json["archives"].append(dir_name)
    if not silent:
        cli.simple_wait_fixed_time("Clearing old events and errors", "Errors and events cleared", 3, vanish=True,
                                   green=True)
    events.save()
    errors.save()
    archives_info.save()


def recount():
    """
    Recount errors / events in overall database
    :return:
    """
    archive_info = JSONFile("data/archive/archive.json",
                            default=str({"last": 0, "total": {"errors": 0, "events": 0}, "archives": []}).replace("\'",
                                                                                                                  "\""))
    if len(archive_info.json["archives"]) == 0:
        cli.success("No archives registered, done!")
        sys.exit()
    total = {"events": 0, "errors": 0}
    progress = cli.progress_bar("Counting errors", vanish=True)
    archives = len(archive_info.json["archives"])
    archives_checked = 0
    for dir_name in archive_info.json["archives"]:
        progress.update_message(f"Counting {dir_name} ({archives_checked}/{archives})",
                                done=(archives_checked / archives) * 100)
        archive_data, archived_errors, archived_events = JSONFile(f"data/archive/{dir_name}/data.json"), JSONFile(
            f"data/archive/{dir_name}/errors.json"), JSONFile(f"data/archive/{dir_name}/events.json")
        nr_errors = len(archived_errors.json)
        nr_events = len(archived_events.json)
        archive_data.json["stats"]["errors"] = nr_errors
        archive_data.json["stats"]["events"] = nr_events
        total["events"] = total["events"] + nr_events
        total["errors"] = total["errors"] + nr_errors
    progress.complete("Checked all archives!")
    errors, events = total["errors"], total["events"]
    cli.success(f"Count complete: {errors} errors & {events} events!")
    archive_info.json["total"]["errors"], archive_info.json["total"]["events"] = errors, events
    cli.simple_wait_fixed_time("Saving...", "Saved!", 3)
    archive_info.save()


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description='Archive events & errors')
        parser.add_argument('--silent', dest='silent', action="store_true",
                            default=False,
                            help='Proceed without taking time and asking for user input')
        parser.add_argument('--recount', dest='recount', action="store_true",
                            help="Recount errors and events.")
        args = parser.parse_args()
        if args.recount:
            recount()
        else:
            main(args.silent)
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        sys.exit()
else:
    print("ERROR: File was imported!")
    sys.exit()
