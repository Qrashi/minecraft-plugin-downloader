from subprocess import run, PIPE
from typing import Dict

from .cli_provider import cli
from utils.context_manager import context
from .errors import report
from .files import pool
from shutil import copy


def replace(string: str, replaceable: Dict[str, str]) -> str:
    replaced = string
    for this, that in replaceable.items():
        replaced.replace(this, str(that))
    return replaced


def execute(task: dict, directory: str, replaceable: Dict[str, str], final_dest: str = "") -> bool:
    task_type = task["type"]
    if task_type == "run":
        code = run(replace(task["value"], replaceable), stdout=PIPE, stderr=PIPE, cwd=directory, shell=True)
        if code.returncode != 0:
            # Wrong return code
            cli.fail(f"Error while executing task {task_type} for {context.software}: return code {code.returncode}")
            report(context.failure_context.failure_severity, "Task \"run\" failure - return code " + str(code),
                   "Shell returned code " + str(code) + ", update of " + context.software + " failed!",
                   exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr),
                   software=context.software)
            return False
        return True
    elif task_type == "write":
        # Write data to file
        file = pool.open(task["value"])
        for change in task["value"]["changes"][:-1]:
            current = file.json
            for access in change["path"]:
                current = current[access]
            current[task["value"]["changes"][-1]] = replace(change["value"], replaceable)
        return True

    elif task_type == "end" and final_dest != "":
        # Copy a file to it's final destination (into the soures folder) to keep it updated
        try:
            copy(task["value"], final_dest)
        except Exception as e:
            cli.fail(f"Error while executing task \"end\" for {context.software}: {e}")
            report(context.failure_severity, f"Task executor - updating {context.software}",
                   "Task \"end\" failure - could not copy file to final destination!", software=context.software,
                   exception=e, additional="File will be cleaned up and deleted - NOT updated")
            return False
        return True
    report(context.failure_severity, "Task \"" + task_type + "\" not found while updating " + context.software,
           "Task not found")
    return False
