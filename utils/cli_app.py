from time import sleep
from typing import Callable

from colorama import Fore, Style, init


# The idea:
# No matter what, a new instruction clears the current row. using \r and filler times column size. Furthermore, we
# check that no message exceeds the column limit set using get_terminal_size(). If a message is set to vanish afterwards,
# we dont print a \n at the end. We should also use a "vetter_print" function that automatically does all that and also
# handles \n or no \n


def clean_print(message: str, vanish: bool):
    if vanish:
        end = ""
    else:
        end = "\n"
    print('\r\x1b[2K\r' + message, end=end + Style.RESET_ALL)


def debug(message: str, vanish=False):
    clean_print(
        Style.DIM + Fore.WHITE + "i DBG " + Style.RESET_ALL + "| " + Fore.WHITE + Style.NORMAL + Style.BRIGHT + message,
        vanish)


class CLIApp:

    def updateSender(self, sender):
        if len(sender) > 3:
            insert = sender[:2]
        elif len(sender) == 1:
            insert = " " + sender + " "
        elif len(sender) == 2:
            insert = sender + " "
        else:
            insert = sender
        self.__sender = Style.DIM + " " + insert + " " + Style.RESET_ALL + "| "

    def getSender(self):
        return self.__sender

    def __init__(self, sender):
        init()  # Required in some cases for windows systems
        self.__sender = "ERR"
        self.positions = ["|-    |", "| -   |", "|  -  |", "|   - |", "|    -|", "|    -|", "|   - |", "|  -  |",
                          "| -   |", "|-    |"]
        self.updateSender(sender)

    def ask(self, message, vanish=False) -> str:
        clean_print(Fore.MAGENTA + Style.BRIGHT + "?" + self.__sender + Fore.MAGENTA + message, True)
        result = input("")
        if vanish:
            print('\x1b[1A\x1b[2K', end="")
        return result

    def info(self, message: str, vanish=False):
        clean_print(Fore.LIGHTBLUE_EX + Style.BRIGHT + "i" + self.__sender + Fore.LIGHTBLUE_EX + message, vanish)

    def warn(self, message: str, vanish=False):
        clean_print(Fore.YELLOW + Style.BRIGHT + "!" + self.__sender + Fore.YELLOW + message, vanish)

    def success(self, message: str, vanish=False):
        clean_print(Fore.GREEN + Style.BRIGHT + "✔" + self.__sender + Fore.GREEN + message, vanish)

    def fail(self, message: str, vanish=False):
        clean_print(Fore.RED + Style.BRIGHT + "!" + self.__sender + Fore.RED + message, vanish)

    def say(self, message: str, vanish=False):
        clean_print(Style.BRIGHT + "#" + self.__sender + message, vanish)

    def load(self, message: str, vanish=False):
        clean_print(Style.BRIGHT + Fore.BLUE + ">" + self.__sender + Fore.BLUE + message, vanish)

    def simple_wait_fixed_time(self, message: str, end_message: str, time: int, vanish=False):

        def get_clock(position):
            return Style.BRIGHT + Fore.LIGHTYELLOW_EX + self.positions[position]

        clean_print(get_clock(0) + Fore.LIGHTYELLOW_EX + message + Style.RESET_ALL, True)
        pos = 1
        for second in range(0, time * 4):
            sleep(0.25)
            pos = pos + 1
            clean_print(get_clock(pos) + Fore.LIGHTYELLOW_EX + Style.NORMAL + " " + message + Style.RESET_ALL, True)
            if pos == len(self.positions) - 1:
                pos = -1
        sleep(0.25)
        clean_print(
            "\r" + Style.BRIGHT + Fore.LIGHTYELLOW_EX + "✔" + self.__sender + Fore.LIGHTYELLOW_EX + end_message + Style.RESET_ALL,
            vanish)

    def progress_bar(self, message, multiplier=1, vanish=False):
        class ProgressBar:
            def __init__(self, sender, multiplier):
                self.__sender = sender
                self.__message = message
                self.__multiplier = multiplier
                self.update(0)

            def update_message(self, message):
                self.__message = message
                self.update(0)

            def fail(self, message):
                clean_print(Style.BRIGHT + Fore.RED + "!" + self.__sender + Fore.RED + message, False)
                # A failure will always stay in CLI

            def update(self, done):
                done_modified = int(done * self.__multiplier)
                clean_print(Style.BRIGHT + Fore.CYAN + "⤓" + self.__sender + Fore.CYAN + "[" + (
                        '=' * done_modified) + (' ' * int(
                    100 * self.__multiplier - done_modified)) + '] ' + self.__message + " ", True)

            def complete(self, message):
                clean_print("\r" + Style.BRIGHT + Fore.CYAN + "✔" + self.__sender + Fore.CYAN + message, vanish)

        return ProgressBar(self.__sender, multiplier)

    def wait_until_event(self, message: str, end_message: str, vanish=False) -> Callable:

        from threading import Thread, Event

        condition = Event()

        def get_clock(position):
            return Style.BRIGHT + Fore.LIGHTYELLOW_EX + self.positions[position]

        def display_loading():
            pos = 1
            while not condition.is_set():
                sleep(0.1)
                pos = pos + 1
                clean_print(get_clock(pos) + Fore.LIGHTYELLOW_EX + Style.NORMAL + " " + message + Style.RESET_ALL + " ",
                            True)
                if pos == len(self.positions) - 1:
                    pos = -1
            clean_print(
                Style.BRIGHT + Fore.LIGHTYELLOW_EX + "✔" + self.__sender + Fore.LIGHTYELLOW_EX + end_message + Style.RESET_ALL,
                vanish)

        clean_print(get_clock(0) + Fore.LIGHTYELLOW_EX + message + Style.RESET_ALL, True)
        Thread(target=display_loading, args=()).start()

        def endfunction():
            condition.set()
            sleep(0.01)

        return endfunction
