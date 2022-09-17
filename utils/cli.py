"""
This file handles the command line interface of the program
"""
from __future__ import annotations

from math import floor
import sys
from time import sleep
from typing import Callable

from .file_defaults import CONFIG
from singlejson import JSONFile

# Try to install colorama
try:
    from colorama import Fore, Style, init

    init()  # Required in some cases for Windows systems
except Exception as e_first:
    print("Error: Could not import / initialize colorama! Please install all dependencies (how-to in README.md)!")
    print(e_first)
    print("Attempting to install colorama")
    import os

    os.system("pip install -r requirements.txt")
    try:
        from colorama import Fore, Style, init

        init()
        print("Successfully installed dependencies, resuming...")
    except Exception as e_second:
        print("Could not auto-install dependencies. Please follow the instructions in README.md")
        from .errors import report

        report(10, "CLI", "Could not start CLI output provider, dependencies missing!",
               exception=str(e_first) + "\nAfter attempting to auto-install: " + str(e_second))
        sys.exit(1)

try:
    from os import get_terminal_size

    terminal_size = get_terminal_size().columns - 5
except Exception as e:
    config = JSONFile("data/config.json", default=CONFIG).json
    if "terminal_fallback_size" in config:
        terminal_size = config["terminal_fallback_size"]
    else:
        from .errors import report

        report(10, "CLI", "Could not retrieve terminal size, aborting! (No fallback size set in config.json)",
               additional="Add \"terminal_fallback_size\": 30 (minimum us 21) to \"data/config.json\"", exception=e)
        print("Error: Could not retrieve terminal size.")
        print("Please configure a terminal size in config.json")
        print("\n1. Open config.json in data")
        print(
            "2. Add \"terminal_fallback_size\" and set it to a number that represents the number of columns in your terminal.")
        print("\nExample:\n\"terminal_fallback_size\": 30 (minimum is 21)")
        print("\nAfter saving the file, please execute this file again!")
        terminal_size = 0
        sys.exit()

if terminal_size < 20:
    print(Fore.RED + Style.BRIGHT + "Error: Unsupported terminal size, output might look ugly!" + Style.RESET_ALL)
    sleep(2)
    terminal_size = 1000

config = JSONFile("data/config.json", default=CONFIG)
if "moon_mode" in config.json and config.json["moon_mode"]:
    loading_small = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
else:
    loading_small = ["/", "|", "\\", "-"]
loading_big = ["|#   |", "| #  |", "|  # |", "|   #|", "|   #|", "|  # |", "| #  |", "|#   |"]

if "max_progressbar_size" in config.json:
    max_progress_size = config.json["max_progressbar_size"]
else:
    max_progress_size = 20


def cut_string(to_split: str, maximum: int) -> str:
    """
    Splits a sentence into two parts
    :param to_split: The string to split
    :param maximum: Where to start splitting
    :return:
    """
    for i in range(0, len(to_split) - maximum):
        index = maximum - i
        if to_split[index] == " ":
            # Split here
            if i <= 1:
                continue
            return to_split[:index] + ("." * min(3, i))
    return to_split[:maximum - 3] + "..."


class SenderHolder:
    """
    A class to hold the current sender
    """

    __sender: str = " ERR |"

    def update(self, new_sender: str):
        """
        Update the sender
        :param new_sender: new sender
        :return:
        """
        self.__sender = new_sender

    def get_sender(self) -> str:
        """
        Get the current sender
        :return: The current sender
        """
        return self.__sender


sender = SenderHolder()


def print_pretty(color: str, symbol: str, message: str, vanish: bool, enable_len_check: bool = True):
    """
    Print a formatted string
    :param color: Color of symbol
    :param symbol: Symbol to print
    :param message: Formatted message to print
    :param vanish: weather to make the message vanish
    :param enable_len_check: enable check if message fits line
    :return:
    """
    if vanish:
        end = ""
    else:
        end = "\n"
    # The length of the "! UPD | " is fixed at 8 characters.
    if len(message) + 8 > terminal_size and enable_len_check:
        # WON'T FIT IN ONE LINE
        message = cut_string(message, terminal_size - 8)
    print('\r\x1b[2K\r' + color + symbol + sender.get_sender() + color + " " + message, end=end + Style.RESET_ALL)


def update_sender(new_sender: str):
    """
    Update the sender (first three letters) of the cli
    :param new_sender:
    :return:
    """
    if len(new_sender) > 3:
        insert = new_sender[:2]
    elif len(new_sender) == 1:
        insert = " " + new_sender + " "
    elif len(new_sender) == 2:
        insert = new_sender + " "
    else:
        insert = new_sender
    sender.update(Style.DIM + " " + insert + " " + Style.RESET_ALL + "|")


def ask(message: str, vanish: bool = False) -> str:
    """
    Ask some question to the user
    :param message: Question to ask
    :param vanish: Weather or not the message should vanish
    :return: the answer as a string
    """
    print_pretty(Fore.MAGENTA, "?", message, True)
    result = input("")
    if vanish:
        print('\x1b[1A\x1b[2K', end="")
    return result


def info(message: str, vanish: bool = False):
    """
    Inform the user of something
    :param message: Information to give to user
    :param vanish: Weather or not the message should vanish
    :return:
    """
    print_pretty(Fore.LIGHTBLUE_EX, "i", message, vanish)


def warn(message: str, vanish: bool = False):
    """
    Warn the user of something
    :param message: Warning to give to user
    :param vanish: Weather or not the message should vanish
    :return:
    """
    print_pretty(Fore.YELLOW, "!", message, vanish)


def success(message: str, vanish: bool = False):
    """
    Indicate success of a task
    :param message: Message sent to user
    :param vanish: Weather or not the message should vanish
    :return:
    """
    print_pretty(Fore.GREEN, "✔", message, vanish)


def fail(message: str, vanish: bool = False):
    """
    Indicate failure of a task
    :param message: Message sent to user
    :param vanish: Weather or not the message should vanish
    :return:
    """
    print_pretty(Fore.RED, "!", Fore.RED + message, vanish)


def say(message: str, vanish: bool = False):
    """
    Tell the user something, neutral
    :param message: message to display
    :param vanish: Weather or not the message should vanish
    :return:
    """
    print_pretty("", "#", message, vanish)


def loading(message: str, vanish: bool = False):
    """
    Tell the user something is loading
    :param message: Message to user
    :param vanish: Weather or not the message should vanish
    :return:
    """
    print_pretty(Fore.BLUE, ">", message, vanish)


def simple_wait_fixed_time(message: str, end_message: str, time: int, vanish: bool = False,
                           green: bool = False):
    """
    Display a message for a fixed amount of time. Execution of your programm will be stopped while this is "ticking"
    :param message: Message to display
    :param end_message: Message to display at end of timeframe.
    :param time: Time to display the message
    :param vanish: Weather or not the message should vanish
    :param green: Weather or not the loading bar should be green.
    :return:
    """
    print_pretty(Fore.LIGHTYELLOW_EX, loading_small[0], loading_big[0] + " " + message, True)
    pos_small = 1
    pos_big = 1
    for _ in range(0, time * 4):
        sleep(0.25)
        pos_small = pos_small + 1
        pos_big = pos_big + 0.5
        print_pretty(Fore.LIGHTYELLOW_EX, loading_small[pos_small], loading_big[int(pos_big)] + " " + message, True)
        if pos_small == len(loading_small) - 1:
            pos_small = -1
        if int(pos_big) == len(loading_big) - 1:
            pos_big = -1
    sleep(0.25)
    if green:
        print_pretty(Fore.GREEN, "✔", end_message, vanish)
    else:
        print_pretty(Fore.LIGHTYELLOW_EX, "✔", end_message, vanish)


def progress_bar(message, progress: int = 0, vanish: bool = False):
    """
    Return a progress bar object
    :param message: Starting message to display
    :param vanish: Weather or not the message should vanish
    :return: A ProgressBar object
    """

    class ProgressBar:
        """
        A ProgressBar utility class
        """

        __message = message
        __progress = progress
        __multiplier = 0

        def __init__(self):
            """
            Initialize the ProgressBar
            """
            self.calculate_multiplier()
            self.update(progress)

        def calculate_multiplier(self):
            """
            Calculate the multiplier (how many symbols the bar can fit)
            :return:
            """
            space_left = min(terminal_size - 8 - len(
                self.__message) + 2, max_progress_size)  # 8 is the length of "⤓ TST | "; 2 are the [] brackets
            if space_left >= 100:  # Maximum sized bar
                self.__multiplier = 1
                return
            self.__multiplier = round(floor(space_left * 0.1) * 0.1, 1)
            # Round to the lowest ten and multiply by 0.1 so that 80 gets 0.8 and only take one decimal

        def update_message(self, updated_message: str, done: int = __progress):
            """
            Update the message of the ProgressBar
            :param updated_message: Updated message to display
            :param done: progress (%), 0 - 100
            :return:
            """
            self.__message = updated_message
            self.__progress = done
            self.calculate_multiplier()
            self.show()

        @staticmethod
        def fail(fail_message: str, ):
            """
            End the ProgressBar with a failed execution indicator
            :param fail_message: Message to display
            :return:
            """
            print_pretty(Fore.RED, "!", fail_message, False)
            # A failure will always stay in CLI

        @staticmethod
        def complete(complete_message: str, green: bool = False):
            """
            Complete a task
            :param complete_message: Message to     display
            :param green: Wetter to use green color coding
            :return:
            """
            if green:
                print_pretty(Fore.GREEN, "✔", complete_message, vanish)
            else:
                print_pretty(Fore.CYAN, "✔", complete_message, vanish)

        def update(self, done: int):
            """
            Update the progress and show the progress bar
            :param done: Progress (0 - 100)
            :return:
            """
            self.__progress = done
            self.show()

        def show(self):
            """
            Show the ProgressBar
            :return:
            """
            done_modified = int(self.__progress * self.__multiplier)
            print_pretty(Fore.CYAN, "⤓", "[" + ('=' * done_modified) +
                         (' ' * int(100 * self.__multiplier - done_modified)) + '] ' + self.__message,
                         True, enable_len_check=False)

    return ProgressBar()


def wait_until_event(message: str, end_message: str, vanish: bool = False, green: bool = False) -> Callable:
    """
    Show a waiting indicator until the returned stop function is called.
    :param message: Message to display
    :param end_message: Message to display at the end of the waiting
    :param vanish: Weather or not the message should vanish
    :param green: Weather or not the message should use green color coding
    :return: A function to terminate the waiting
    """
    from threading import Thread, Event
    condition = Event()

    def display_loading():
        """
        Display the loading animation and check for termination of waiting
        :return:
        """
        pos_small = 0
        pos_big = 0
        while not condition.is_set():
            sleep(0.1)
            pos_small = pos_small + 1
            pos_big = pos_big + 0.5
            print_pretty(Fore.LIGHTYELLOW_EX, loading_small[pos_small], loading_big[int(pos_big)] + " " + message,
                         True)
            if pos_small == len(loading_small) - 1:
                pos_small = 0
            if int(pos_big) == len(loading_big) - 1:
                pos_big = 0
        if green:
            print_pretty(Fore.GREEN, "✔", end_message, vanish)
        else:
            print_pretty(Fore.LIGHTYELLOW_EX, "✔", end_message, vanish)

    print_pretty(Fore.LIGHTYELLOW_EX, loading_small[0], loading_big[0] + " " + message, True)
    Thread(target=display_loading, args=()).start()

    def end():
        """
        End waiting for a condition
        :return:
        """
        condition.set()
        sleep(0.01)

    return end
