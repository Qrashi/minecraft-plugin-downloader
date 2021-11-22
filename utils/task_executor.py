from subprocess import run, PIPE
from shutil import copy
from typing import Callable
from distutils.dir_util import copy_tree

from .cli_provider import cli
from .error import report


def execute(task: dict, directory: str, replace: Callable[[str], str], final_file: str, source_name: str, last_check: str, severity: int) -> bool:
    type = task["type"]
    if type == "run":
        code = run(replace(task["value"]), stdout=PIPE, stderr=PIPE, cwd=directory, shell=True)  # TODO: Retrieve output and store it in error
        if code.returncode != 0:
            # Wrong return code
            cli.fail("Error while executing task " + type + " for " + source_name)
            report("Task \"run\" failure - return code " + str(code), severity, "Shell returned code " + str(code) + ", update of " + source_name + " failed!", additional="Last update: " + last_check, exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr))
            return False
        return True
    elif type == "end":
        if "file" in task["value"]:
            # Copy the specified file to the tmp file
            try:
                copy(directory + "/" + replace(task["value"]["file"]), final_file)
            except Exception as e:
                cli.fail("Error while cleaning up tasks, result copy failed")
                print(e)
                report("Task \"end\" failure - could not copy results", severity, "Could not copy result file for " + source_name,
                       additional="Last update: " + last_check, exception=e)
                return False
        if "keep" in task["value"]:
            try:
                copy_tree(directory, replace(task["value"]["keep"]))
            except Exception as e:
                cli.fail("Error while cleaning up tasks, temporary directory copy failed")
                print(e)
                report("Task \"end\" failure - could not copy temporary directory", severity, "Could not copy temporary directory for " + source_name + " (" + directory + ")",
                       additional="Last update: " + last_check, exception=e)
                return False
        if len(task["value"]) == 0:  # If there are no values, ERRORR
            report("Task \"" + type + "\" did not specify any actions!", 0, "No fatal error, could be configuration issue", additional="Last update: " + last_check)
        return True

    # TODO: Add "write" and "copy" task

    report("Task \"" + type + "\" not found", severity, "Task not found", additional="Last update: " + last_check)
    return False

