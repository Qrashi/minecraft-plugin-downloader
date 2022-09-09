from subprocess import run, PIPE
from typing import Dict

from .cli_provider import cli
from utils.context_manager import context
from .errors import report
from .files import pool


def replace(string: str, replaceable: Dict[str, str]) -> str:
    replaced = string
    for this, that in replaceable.items():
        replaced.replace(this, str(that))
    return replaced


def execute(task: dict, directory: str, replaceable: Dict[str, str]) -> bool:
    task_type = task["type"]
    if task_type == "run":
        code = run(replace(task["value"], replaceable), stdout=PIPE, stderr=PIPE, cwd=directory, shell=True)
        if code.returncode != 0:
            # Wrong return code
            cli.fail("Error while executing task " + task_type + " for " + context.software)
            report(context.failure_context.failure_severity, "Task \"run\" failure - return code " + str(code),
                   "Shell returned code " + str(code) + ", update of " + context.software + " failed!",
                   exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr),
                   software=context.software)
            return False
        return True
    if task_type == "write":
        # Write data to file
        file = pool.open(task["value"])
        for change in task["value"]["changes"][:-1]:
            current = file.json
            for access in change["path"]:
                current = current[access]
            current[task["value"]["changes"][-1]] = replace(change["value"], replaceable)
        return True

    report(context.failure_severity, "Task \"" + task_type + "\" not found while updating " + context.software,
           "Task not found")
    return False
