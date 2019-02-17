import inspect
import sys
import os

def split_path(path):
    """
    Splits the given path into all its components.

    Returns:
        List[str]: A list of all the element in this path.
    """
    head, tail = os.path.split(path)
    if head == path:
        return [head]
    else:
        return split_path(head) + [tail]

class Logger(object):
    VERBOSE = 0
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    SILENT = 50

    def __init__(self, severity=INFO, path_depth=3):
        """
        Logger.

        Optional Args:
            severity (Logger.Severity): Messages below this severity are ignored.
            path_depth (int): The depth of the displayed path. If this is set to -1, the absolute path is displayed.
        """
        self.severity = severity
        self.path_depth = path_depth

    @staticmethod
    def severity_color_prefix(sev):
        prefix = "\033[1;"
        color = {Logger.VERBOSE: "90m", Logger.DEBUG: "90m", Logger.INFO: "92m", Logger.WARNING: "95m", Logger.ERROR: "31m"}[sev]
        return prefix + color if color else ""

    def assemble_message(self, message, stack_depth, prefix):
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

    def log(self, message, severity):
        if severity >= self.severity and not self.severity == Logger.SILENT:
            print("{:}{:}\033[0m".format(Logger.severity_color_prefix(severity), message))

    def verbose(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="V"), Logger.VERBOSE)

    def debug(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="D"), Logger.DEBUG)

    def info(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="I"), Logger.INFO)

    def warning(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="W"), Logger.WARNING)

    def error(self, message):
        self.log(self.assemble_message(message, stack_depth=2, prefix="E"), Logger.ERROR)

G_LOGGER = Logger()
