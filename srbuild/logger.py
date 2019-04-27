from typing import List
import inspect
import enum
import sys
import os

def split_path(path) -> List[str]:
    """
    Splits the given path into all its components.

    Returns:
        List[str]: A list of all the element in this path.
    """
    head, tail = os.path.split(path)
    return [head] if head == path else split_path(head) + [tail]

class Color(enum.Enum):
    DEFAULT = "0m"
    GRAY = "90m"
    GREEN = "92m"
    PURPLE = "95m"
    RED = "31m"

class Logger(object):
    VERBOSE = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    def __init__(self, severity=INFO, path_depth=3):
        """
        Logger.

        Optional Args:
            severity (Logger.Severity): Messages below this severity are ignored.
            path_depth (int): The depth of the displayed path. If this is set to -1, the absolute path is displayed.
        """
        self.severity = severity
        self.path_depth = path_depth

    def assemble_message(self, message, stack_depth, prefix) -> str:
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

    def log(self, message, severity, color=Color.DEFAULT):
        # Disable logging when running with -O.
        if __debug__ and severity >= self.severity:
            print("\033[1;{:}{:}\033[0m".format(color.value, message))

    def verbose(self, message, color=Color.GRAY):
        self.log(self.assemble_message(message, stack_depth=2, prefix="V"), severity=Logger.VERBOSE, color=color)

    def debug(self, message, color=Color.DEFAULT):
        self.log(self.assemble_message(message, stack_depth=2, prefix="D"), severity=Logger.DEBUG, color=color)

    def info(self, message, color=Color.GREEN):
        self.log(self.assemble_message(message, stack_depth=2, prefix="I"), severity=Logger.INFO, color=color)

    def warning(self, message, color=Color.PURPLE):
        self.log(self.assemble_message(message, stack_depth=2, prefix="W"), severity=Logger.WARNING, color=color)

    def error(self, message, color=Color.RED):
        self.log(self.assemble_message(message, stack_depth=2, prefix="E"), severity=Logger.ERROR, color=color)

    def critical(self, message, color=Color.RED):
        message = self.assemble_message(message, stack_depth=2, prefix="E")
        self.log(message, severity=Logger.ERROR, color=color)
        sys.exit(1)

G_LOGGER = Logger()
