from srbuild.tools.flags import BuildFlags
from srbuild.tools import compiler
from srbuild.logger import G_LOGGER
import srbuild.utils as utils
from typing import List, Union
import abc

# Responsible for translating srbuild.tools.flags.BuildFlags to actual command-line flags.
# This class defines everything about each linker by supplying a unified interface.
# That means that Linker can blindly use any LinkerDef to generate valid build commands.
class LinkerDef(abc.ABC):
    @staticmethod
    def executable() -> str:
        """
        Specifies executable associated with this LinkerDef.
        For example, this would return "clang" for Clang.

        Returns:
            str: The executable path.
        """
        pass

    @staticmethod
    def shared() -> str:
        """
        Specifies shared flag for this LinkerDef.
        For example, this would return "-shared" for Clang.

        Returns:
            str: The compile-only flag.
        """
        pass

    @staticmethod
    def output(path: str) -> str:
        """
        Specifies command-line arguments for outputting to the specified location.
        For example, this would return "-opath" for Clang.

        Returns:
            str: The required arguments.
        """
        pass

    @staticmethod
    def lib_dir(path: str) -> str:
        """
        Specifies command-line arguments for adding an library directory.
        For example, this would return "-Lpath" for Clang.

        Returns:
            str: The required arguments.
        """
        pass

    @staticmethod
    def parse_flags(build_flags: BuildFlags) -> List[str]:
        """
        Parses build flags and returns the required command-line arguments.
        """
        pass

# For conventions that are common among Linux compilers.
# The linker flags are largely similar to the compiler flags.
class LinuxLinkerDef(LinkerDef):
    @staticmethod
    def shared() -> str:
        return "-shared"

    @staticmethod
    def output(path: str) -> str:
        return f"-o{path}"

    @staticmethod
    def lib_dir(path: str) -> str:
        return f"-L{path}"

    @staticmethod
    def parse_flags(build_flags: BuildFlags) -> List[str]:
        linker_flags = compiler.LinuxCompilerDef.parse_flags(build_flags) + build_flags._raw
        if build_flags._shared:
            linker_flags.append("-shared")
        return linker_flags

class ClangDef(LinuxLinkerDef):
    @staticmethod
    def executable() -> str:
        return "clang"

class GCCDef(LinuxLinkerDef):
    @staticmethod
    def executable() -> str:
        return "gcc"

# TODO: Use ldconfig to locate libraries.
# Responsible for generating commands that will link the given source files into a shared library or executable.
class Linker(object):
    def __init__(self, ldef: Union[type, LinkerDef]):
        self.ldef = ldef

    # Generates a signature for a given combination of input file and options.
    # If two signatures are the same for an input file, it means the resulting file(s) would be identical.
    # The signature is everything that makes the resulting object file unique - i.e. linker, input file, link directories and linker options.
    # TODO: Revise this
    def signature(self, flags: BuildFlags, shared=False) -> List[str]:
        sig = [self.ldef.executable()] + self.ldef.parse_flags(flags) + [str(shared)]
        return utils.str_hash(sig)

    # Generates the command required to link the inputs files with the specified options.
    def link(self, input_paths: List[str], output_path, lib_dirs: List[str]=[], flags: BuildFlags=BuildFlags()):
        G_LOGGER.debug(f"self.ldef: {self.ldef}")
        linker_flags = self.ldef.parse_flags(flags)
        lib_dirs = [self.ldef.lib_dir(dir) for dir in lib_dirs]
        # The full command.
        cmd = [self.ldef.executable()] + input_paths + linker_flags + lib_dirs + [self.ldef.output(output_path)]
        G_LOGGER.debug(f"Link Command: {' '.join(cmd)}")
        return cmd

clang = Linker(ClangDef)
gcc = Linker(GCCDef)
