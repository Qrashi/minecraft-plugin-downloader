"""
This file handles AccessFields
"""
from typing import Union, Dict, List

from utils.errors import report
from utils.context_manager import context
from utils.file_defaults import CONFIG
from utils.files import pool
from utils.web import get_managed


class FileAccessField:
    """
    A FileAccessField, a way to update and access data of a json file
    """
    def __init__(self, field: Union[Dict[str, Union[str, List[str]]], str]):
        """
        Initialize a FileAccessField
        :param field: The given json data to describe the FileAccessField ({"file": "file.name", "path": ["data"]})
        """
        if type(field) is str:
            self.file = field
            self.path = []
        else:
            self.file = field["file"]
            self.path: List[str] = field["access"]

    def access(self) -> Union[dict, str, int, list, None]:
        """
        Accesses the desired field.
        :return: The accessed field
        """
        json = pool.open(self.file).json
        if len(self.path) == 0:
            return json
        data = json
        for attribute in self.path:
            try:
                data = data[attribute]
            except Exception as e:
                report(context.failure_severity, f"FileAccesField - {context.name} - {context.task}",
                       "Could not access json, some error occured.",
                       additional=f"file: {self.file}; file-content: f{json}; accessing f{self.path} ; trying to access f{attribute} in f{data}",
                       exception=e)
                return None
        return data

    def update(self, new_value: Union[dict, str, int, list]):
        """
        Update the desired field
        :param new_value: Data to update with
        :return:
        """
        json = pool.open(self.file).json
        if len(self.path) == 0:
            json = new_value
        data = json
        for attribute in self.path[:-1]:
            try:
                data = data[attribute]
            except Exception as e:
                report(context.failure_severity, f"FileAccesField - {context.name} - {context.task}",
                       "Could not access json, some error occured",
                       additional=f"file: {self.file}; file-content: f{json}; accessing f{self.path} ; trying to access f{attribute} in f{data}",
                       exception=e)
                return
        data[self.path[-1]] = new_value


def uri_access(path: List[str], json: dict):
    """
    Accesses a dict according to the URIAccessField rules.
    :param path: path to data
    :param json: The json to access
    :return: The accessed field
    """
    if len(path) == 0:
        return json
    data = json
    for attribute in path:
        try:
            data = data[attribute]
        except Exception as e:
            report(context.failure_severity, f"URIAccessField - {context.name} - {context.task}",
                   "Could not access json property, some error occurred.",
                   additional=f"given data: {json} ; accessing f{path};\n trying to access f{attribute} in f{data}",
                   exception=e, software=context.name)
            return None
    return data


class WebAccessField:
    """
    WebAccessField, a component that can easily retrieve information from the internet
    """
    tasks: List[Dict[str, Union[str, List[Union[str, int]]]]]

    def __init__(self, field: Union[Dict, List, str]):
        """
        Initialize a new WebAccessField according to data_info.md
        :param field: The field to construct the WebAccessField. Either a list of tasks, a single task or just a string
        """
        self.replaceable: Dict[str, str] = {}
        # replaceable dict:
        # {"%var%": "value"} NOT {"var": "value"}
        if type(field) is str:
            self.tasks = [
                {
                    "task": "return",
                    "value": field
                }
            ]
        elif type(field) is dict:
            self.tasks = [field]
        else:
            self.tasks = field

    def replace(self, string: str) -> str:
        """
        Replace variables marked with %name% with their respective data
        :param string: The string to perform replacing on
        :return: The string with all the inserted data
        """
        result = string
        for this, that in self.replaceable.items():
            result = result.replace(this, str(that))
        return result

    def execute(self, replaceable: Dict[str, str], requres_return: bool = True, headers: Dict = pool.open("data/config.json", default=CONFIG).json["default_headers"]) -> Union[int, str, List, Dict, bool, None, Exception]:
        """
        Execute the WebAccessField, get the desired value
        :param replaceable: Standard replaceable values
        :param requres_return: Weather a value needs to be returned
        :param headers: The default headers to use
        :return: The retrieved value
        """
        self.replaceable = replaceable
        for task in self.tasks:
            if "type" not in task:
                task["type"] = "get_return"
            if task["type"] == "get_return":
                # Integrity check
                if not all(x in list(task) for x in ["url", "path"]):
                    report(context.failure_severity, f"WebAccessField - {context.name} - {context.task}",
                           "malformed get_return task. \"url\" or \"path\" is missing", additional=f"task data: {task}",
                           software=context.name)
                    return WebAccessFieldError("malformed \"get_return\" task, missing \"url\" or \"path\"!")
                task_headers = headers  # Task specific headers
                if "headers" in task:
                    task_headers = task["headers"]  # Task headers should only be used for THIS task
                result = get_managed(self.replace(task["url"]), task_headers)
                if isinstance(result, Exception):
                    return result
                return uri_access(task["path"], result)
            elif task["type"] == "get_store":
                if not all(x in list(task) for x in ["url", "path", "destination"]):
                    report(context.failure_severity, f"WebAccessField - {context.name} - {context.task}",
                           "malformed get_store task. \"url\", \"path\" or \"destination\" is missing",
                           additional=f"task data: {task}",
                           software=context.name)
                    return WebAccessFieldError(
                        "malformed \"get_store\" task, missing \"url\", \"path\" or \"destination\"!")
                task_headers = headers  # Task specific headers
                if "headers" in task:
                    task_headers = task["headers"]  # Task headers should only be used for THIS task
                destination = task["destination"]
                result = get_managed(self.replace(task["url"]), task_headers)
                if isinstance(result, Exception):
                    return result
                self.replaceable[f"%{destination}%"] = uri_access(task["path"], result)
            elif task["type"] == "set_headers":
                if "headers" in task:
                    headers = task["headers"]
                else:
                    report(context.failure_severity, f"WebAccessField - {context.name} - {context.task}",
                           "malformed set_headers task. \"headers\" is missing",
                           additional=f"task data: {task}",
                           software=context.name)
                    return WebAccessFieldError("task \"set_headers\" malformed, missing \"headers\"")
            elif task["type"] == "return":
                if "value" in task:
                    return self.replace(task["value"])
                report(context.failure_severity, f"WebAccessField - {context.name} - {context.task}",
                       "malformed return task. \"value\" is missing",
                       additional=f"task data: {task}",
                       software=context.name)
                return WebAccessFieldError("task \"return\" malformed, missing \"value\"!")
        if requres_return:
            report(context.failure_severity, f"WebAccessField - {context.name} - {context.task}",
                   "could not complete WebAccesField tasks - no return or get_return task! cannot set value!",
                   additional=f"tasks: {self.tasks}", software=context.name)
            return WebAccessFieldError("could not complete request - no return or get_return task!")
        return None


class WebAccessFieldError(Exception):
    """
    An error which occurred while doing something with a WebAccessField
    """

    pass
