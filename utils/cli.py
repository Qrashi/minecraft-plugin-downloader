from time import sleep
from typing import Callable
from math import floor
from .json import JsonFile

try:
    from colorama import Fore, Style, init

    init()  # Required in some cases for windows systems
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
        report(10, "CLI", "Could not start CLI output provider, dependencies missing!", exception=str(e_first) + "\nAfter attempting to auto-install: " + str(e_second))
        exit(1)

try:
    from os import get_terminal_size

    terminal_size = get_terminal_size().columns - 5
except Exception as e:
    config = JsonFile("data/config.json").json
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
        exit()

if terminal_size < 20:
    print(Fore.RED + Style.BRIGHT + "Error: Unsupported terminal size, output might look ugly!" + Style.RESET_ALL)
    sleep(2)
    terminal_size = 1000

config = JsonFile("data/config.json").json
if "moon_mode" in config:
    loading_small = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
else:
    loading_small = ["/", "|", "\\", "-"]
loading_big = ["|#   |", "| #  |", "|  # |", "|   #|", "|   #|", "|  # |", "| #  |", "|#   |"]


def cut_string(to_split: str, maximum: int) -> str:
    """
    Splits a sentence into two parts.
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


class CLIApp:

    def print(self, color: str, symbol: str, message: str, vanish: bool, enable_len_check: bool = True):
        if vanish:
            end = ""
        else:
            end = "\n"
        # The length of the "! UPD | " is fixed at 8 characters.
        if len(message) + 8 > terminal_size and enable_len_check:
            # WONT FIT IN ONE LINE
            message = cut_string(message, terminal_size - 8)
        print('\r\x1b[2K\r' + color + symbol + self.__sender + color + message, end=end + Style.RESET_ALL)

    def update_sender(self, sender: str):
        if len(sender) > 3:
            insert = sender[:2]
        elif len(sender) == 1:
            insert = " " + sender + " "
        elif len(sender) == 2:
            insert = sender + " "
        else:
            insert = sender
        self.__sender = Style.DIM + " " + insert + " " + Style.RESET_ALL + "| "

    def get_sender(self):
        return self.__sender

    def __init__(self, sender: str):
        self.__sender = "ERR"
        self.update_sender(sender)

    def ask(self, message: str, vanish: bool = False) -> str:
        self.print(Fore.MAGENTA, "?", message, True)
        result = input("")
        if vanish:
            print('\x1b[1A\x1b[2K', end="")
        return result

    def info(self, message: str, vanish: bool = False):
        self.print(Fore.LIGHTBLUE_EX, "i", message, vanish)

    def warn(self, message: str, vanish: bool = False):
        self.print(Fore.YELLOW, "!", message, vanish)

    def success(self, message: str, vanish: bool = False):
        self.print(Fore.GREEN, "✔", message, vanish)

    def fail(self, message: str, vanish: bool = False):
        self.print(Fore.RED, "!", Fore.RED + message, vanish)

    def say(self, message: str, vanish: bool = False):
        self.print("", "#", message, vanish)

    def load(self, message: str, vanish: bool = False):
        self.print(Fore.BLUE, ">", message, vanish)

    def simple_wait_fixed_time(self, message: str, end_message: str, time: int, vanish: bool = False, green: bool = False):
        self.print(Fore.LIGHTYELLOW_EX, loading_small[0], loading_big[0] + " " + message, True)
        pos_small = 1
        pos_big = 1
        for second in range(0, time * 4):
            sleep(0.25)
            pos_small = pos_small + 1
            pos_big = pos_big + 0.5
            self.print(Fore.LIGHTYELLOW_EX, loading_small[pos_small], loading_big[int(pos_big)] + " " + message, True)
            if pos_small == len(loading_small) - 1:
                pos_small = -1
            if int(pos_big) == len(loading_big) - 1:
                pos_big = -1
        sleep(0.25)
        if green:
            self.print(Fore.GREEN, "✔", end_message, vanish)
        else:
            self.print(Fore.LIGHTYELLOW_EX, "✔", end_message, vanish)

    def progress_bar(self, message, vanish: bool = False):
        class ProgressBar:
            def calculate_multiplier(self):
                space_left = terminal_size - 8 - len(
                    self.__message) + 2  # 8 is the length of "⤓ TST | "; 2 are the [] brackets
                if space_left >= 100:  # Maximum sized bar
                    self.__multiplier = 1
                    return
                self.__multiplier = round(floor(space_left * 0.1) * 0.1, 1)  # Round to lowest ten and multiply by 0.1 so that 80 gets 0.8 and only take one decimal

            def __init__(self, print_function):
                self.__print_function = print_function
                self.__message = message
                self.__multiplier = 0
                self.calculate_multiplier()
                self.update(0)

            def update_message(self, updated_message: str, done: int = 0):
                self.__message = updated_message
                self.calculate_multiplier()
                self.update(done)

            def fail(self, fail_message: str, ):
                self.__print_function(Fore.RED, "!", fail_message, False)
                # A failure will always stay in CLI

            def complete(self, complete_message: str, green: bool = False):
                if green:
                    self.__print_function(Fore.GREEN, "✔", complete_message, vanish)
                else:
                    self.__print_function(Fore.CYAN, "✔", complete_message, vanish)

            def update(self, done):
                done_modified = int(done * self.__multiplier)
                self.__print_function(Fore.CYAN, "⤓", "[" + (
                        '=' * done_modified) + (' ' * int(100 * self.__multiplier - done_modified)) + '] ' + self.__message, True, enable_len_check=False)

        return ProgressBar(self.print)

    def wait_until_event(self, message: str, end_message: str, vanish: bool = False, green: bool = False) -> Callable:
        from threading import Thread, Event
        condition = Event()

        def display_loading():
            pos_small = 0
            pos_big = 0
            while not condition.is_set():
                sleep(0.1)
                pos_small = pos_small + 1
                pos_big = pos_big + 0.5
                self.print(Fore.LIGHTYELLOW_EX, loading_small[pos_small], loading_big[int(pos_big)] + " " + message,
                           True)
                if pos_small == len(loading_small) - 1:
                    pos_small = 0
                if int(pos_big) == len(loading_big) - 1:
                    pos_big = 0
            if green:
                self.print(Fore.GREEN, "✔", end_message, vanish)
            else:
                self.print(Fore.LIGHTYELLOW_EX, "✔", end_message, vanish)

        self.print(Fore.LIGHTYELLOW_EX, loading_small[0], loading_big[0] + " " + message, True)
        Thread(target=display_loading, args=()).start()

        def end():
            condition.set()
            sleep(0.01)

        return end
