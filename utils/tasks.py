"""
Task executor for server update and dependency update tasks
"""
from subprocess import run, PIPE
from typing import Dict

import utils.cli as cli
from utils.context_manager import context
from .errors import report
from singlejson import pool
from shutil import copy


def replace(string: str, replaceable: Dict[str, str]) -> str:
    """
    Insert available data into the string
    :param string: string to perform replacing on
    :param replaceable: possible data to replace
    :return: The string inserted with the data
    """
    replaced = string
    for this, that in replaceable.items():
        replaced.replace(this, str(that))
    return replaced


def execute(task: dict, directory: str, replaceable: Dict[str, str], final_dest: str = "") -> bool:
    """
    Execute a task
    :param task: task to execute
    :param directory: directory to execute in
    :param replaceable: Available variables for replacement
    :param final_dest: final destination of source file (only if updating dependencies)
    :return: Weather or not the task succeeded
    """
    task_type = task["type"]
    if task_type == "run":
        code = run(replace(task["value"], replaceable), stdout=PIPE, stderr=PIPE, cwd=directory, shell=True)
        if code.returncode != 0:
            # Wrong return code
            cli.fail(f"Error while executing task {task_type} for {context.name}: return code {code.returncode}")
            report(context.failure_context.failure_severity, "Task \"run\" failure - return code " + str(code),
                   "Shell returned code " + str(code) + ", update of " + context.name + " failed!",
                   exception="Log: stdout:\n" + str(code.stdout) + "\nstderr:\n" + str(code.stderr),
                   software=context.name)
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

    if task_type == "end" and final_dest != "":
        # Copy a file to its final destination (into the sources folder) to keep it updated
        try:
            copy(task["value"], final_dest)
        except Exception as e:
            cli.fail(f"Error while executing task \"end\" for {context.name}: {e}")
            report(context.failure_severity, f"Task executor - updating {context.name}",
                   "Task \"end\" failure - could not copy file to final destination!", software=context.name,
                   exception=e, additional="File will be cleaned up and deleted - NOT updated")
            return False
        return True
    report(context.failure_severity, "Task \"" + task_type + "\" not found while updating " + context.name,
           "Task not found")
    return False
