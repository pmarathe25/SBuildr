from typing import List
import inspect
import enum
import sys
import os

class SBuildrException(Exception):
    pass

class Color(enum.Enum):
    DEFAULT = "0m"
    BOLD = "1m"
    RED = "31m"
    GREEN = "32m"
    BLUE = "34m"
    MAGENTA = "35m"
    CYAN = "36m"
    GRAY = "90m"
    LIGHT_RED = "91m"
    LIGHT_GREEN = "92m"
    LIGHT_BLUE = "94m"
    LIGHT_MAGENTA = "95m"

class Verbosity(enum.IntEnum):
    VERBOSE = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

def plural(text: str, num: int):
    return f"{num} {text}{'s' if num > 1 else ''}"

def split_path(path) -> List[str]:
    """
    Splits the given path into all its components.

    Returns:
        List[str]: A list of all the element in this path.
    """
    head, tail = os.path.split(path)
    return [head] if head == path else split_path(head) + [tail]

def color_string(message, colors: List[Color]) -> str:
    def prefix_join(prefix: str, joinable: List[object]) -> str:
        return (prefix if joinable else "") + prefix.join(joinable)

    color_prefix = prefix_join("\033[", [color.value for color in colors])
    return f"{color_prefix}{message}\033[0m"

class Logger(object):
    def __init__(self, verbosity=Verbosity.INFO, path_depth=3):
        """
        Logger.

        Optional Args:
            :param verbosity: Messages below this verbosity are ignored.
            :param path_depth: The depth of the displayed path. If this is set to -1, the absolute path is displayed.
        """
        self.verbosity = verbosity
        self.path_depth = path_depth

    def assemble_message(self, message, stack_depth, prefix="") -> str:
        # Disable logging when running with -O.
        if not __debug__:
            return ""

        module = inspect.getmodule(sys._getframe(stack_depth))
        # Handle logging from the top-level of a module.
        if not module:
            module = inspect.getmodule(sys._getframe(stack_depth - 1))
        filename = module.__file__
        # Get only a subset of the path, as specified by path_depth
        if self.path_depth == 0:
            return f"{prefix} {message}"
        elif self.path_depth != -1:
            filename = os.path.join(*split_path(filename)[-self.path_depth:])
            return f"{prefix} [{filename}:{sys._getframe(stack_depth).f_lineno}] {message}"

    def log(self, message: str, verbosity: Verbosity=Verbosity.INFO, colors: List[Color]=[Color.DEFAULT]):
        # Disable logging when running with -O.
        if __debug__ and verbosity >= self.verbosity:
            print(color_string(message, colors))

    def verbose(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="V"), verbosity=Verbosity.VERBOSE, colors=[Color.BOLD, Color.GRAY])

    def debug(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="D"), verbosity=Verbosity.DEBUG)

    def info(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="I"), verbosity=Verbosity.INFO, colors=[Color.BOLD, Color.GREEN])

    def warning(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="W"), verbosity=Verbosity.WARNING, colors=[Color.BOLD, Color.MAGENTA])

    def error(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="E"), verbosity=Verbosity.ERROR, colors=[Color.BOLD, Color.RED])

    def critical(self, message):
        message = self.assemble_message(message, stack_depth=2, prefix="C")
        self.log(message, verbosity=Verbosity.CRITICAL, colors=[Color.BOLD, Color.RED])
        raise SBuildrException(message)

G_LOGGER = Logger()
