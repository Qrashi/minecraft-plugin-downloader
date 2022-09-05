from distutils.dir_util import copy_tree
from shutil import copy
from subprocess import run, PIPE
from typing import Callable

from .cli_provider import cli
from .errors import report
from .files import pool


def execute(task: dict, directory: str, replace: Callable[[str], str], final_file: str, source_name: str,
            last_check: str, severity: int) -> bool:
    task_type = task["type"]
    if task_type == "run":
        code = run(replace(task["value"]), stdout=PIPE, stderr=PIPE, cwd=directory, shell=True)
        if code.returncode != 0:
            # Wrong return code
            cli.fail("Error while executing task " + task_type + " for " + source_name)
            report(severity, "Task \"run\" failure - return code " + str(code),
                   "Shell returned code " + str(code) + ", update of " + source_name + " failed!",
                   additional="Last update: " + last_check,
                   exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr))
            return False
        return True
    if task_type == "end":
        if "file" in task["value"]:
            # Copy the specified file to the tmp file
            try:
                copy_path = replace(task["value"]["file"])
                if not copy_path.startswith("/"):
                    copy_path = directory + "/" + copy_path
                copy(copy_path, final_file)
            except Exception as e:
                cli.fail("Error while cleaning up tasks, result copy failed")
                print(e)
                report(severity, "Task \"end\" failure - could not copy results",
                       "Could not copy result file for " + source_name, additional="Last update: " + last_check,
                       exception=e)
                return False
        if "keep" in task["value"]:
            try:
                copy_tree(directory, replace(task["value"]["keep"]))
            except Exception as e:
                cli.fail("Error while cleaning up tasks, temporary directory copy failed")
                print(e)
                report(severity, "Task \"end\" failure - could not copy temporary directory",
                       "Could not copy temporary directory for " + source_name + " (" + directory + ")",
                       additional="Last update: " + last_check, exception=e)
                return False
        if len(task["value"]) == 0:  # If there are no values, ERROR
            report(0, "Task \"" + task_type + "\" did not specify any actions!",
                   "No fatal error, could be configuration issue", additional="Last update: " + last_check)
        return True
    if task_type == "write":
        # Write data to file
        file = pool.open(task["value"])
        for change in task["value"]["changes"]:
            current = file.json
            for access in change["path"]:
                current = current[access]
            current = replace(change["value"])
        return True

    report(severity, "Task \"" + task_type + "\" not found", "Task not found", additional="Last update: " + last_check)
    return False
