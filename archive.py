from utils.cli_provider import cli
from utils.jsonFile import JsonFile


def main():
    cli.update_sender("ARM")
    cli.load("Accessing recent errors & events...", vanish=True)
    errors_file, events_file = JsonFile("data/errors.json"), JsonFile("data/events.json")
    cli.info(
        "Preparing to archive " + str(len(errors_file.json)) + " errors and " + str(len(events_file.json)) + " events.")
    if cli.ask("Are you sure? (y, yes) ", vanish=True) in ["y", "yes"]:
        progress = cli.progress_bar("Archiving errors & events...")
        errors_destination_file, events_destination_file = JsonFile("data/archive/all_errors.json",
                                                                    default="[]"), JsonFile(
            "data/archive/all_events.json", default="[]")
        errors = len(errors_file.json)
        moved = 0
        for error in errors_file.json:
            errors_destination_file.json.append(error)
            moved = moved + 1
            progress.update((((errors - moved) / errors) * 100) / 2)
        events = len(events_file.json)
        moved = 0
        for event in events_file.json:
            events_destination_file.json.append(event)
            progress.update((((events - moved) / events) * 100) / 2)
        progress.complete("Moved all errors & events into archive.")

        errors_file.json = []
        events_file.json = []

        cli.simple_wait_fixed_time("Saving configurations, CRTL + C to abort [3s]", "Saved!", 3, vanish=True)
        errors_file.save()
        events_file.save()
        events_destination_file.save()
        errors_destination_file.save()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cli.fail("Aborted, no data saved!")
        exit()
else:
    print("Bitte blasen Sie mir die Huf auf!")
    exit()
