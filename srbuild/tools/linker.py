from srbuild.tools.flags import BuildFlags
from srbuild.tools import compiler
from srbuild.logger import G_LOGGER
import srbuild.utils as utils

from typing import List, Union
import abc
import os

# TODO: Detect whether libstdc++ or libc++ is available on the system.

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
    def lib(name: str) -> str:
        """
        Specifies command-line arguments for linking a library.
        For example, this would return "-lname" for Clang.

        Returns:
            str: The required arguments.
        """
        pass

    @staticmethod
    def to_lib(name: str) -> str:
        """
        Given the name of a library, specifies the basename of the corresponding file.
        For example, on Linux, to_lib("stdc++") would return "libstdc++.so"

        Returns:
            str: The basename of the library.
        """
        pass

    @staticmethod
    def to_exec(name: str) -> str:
        """
        Given the name of a executable, specifies the basename of the corresponding file.
        For example, on Windows, to_exec("test") would return "test.exe"

        Returns:
            str: The basename of the library.
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
    def lib(name: str) -> str:
        return f"-l{name}"

    @staticmethod
    def to_lib(name: str) -> str:
        return f"lib{name}.so"

    @staticmethod
    def to_exec(name: str) -> str:
        return name

    @staticmethod
    def parse_flags(build_flags: BuildFlags) -> List[str]:
        linker_flags: List[str] = compiler.LinuxCompilerDef.parse_flags(build_flags)
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
    # TODO(0): Revise this
    def signature(self, input_paths: List[str], libs: List[str]=[], lib_dirs: List[str]=[], flags: BuildFlags=BuildFlags()) -> str:
        # Order of inputs does not matter, but order of libs does. TODO: Check if that's true
        sig = [self.ldef.executable()] + list(sorted(input_paths)) + self.ldef.parse_flags(flags) + libs + lib_dirs
        return utils.str_hash(sig)

    # Generates the command required to link the inputs files with the specified options.
    def link(self, input_paths: List[str], output_path, libs: List[str]=[], lib_dirs: List[str]=[], flags: BuildFlags=BuildFlags()) -> List[str]:
        G_LOGGER.debug(f"self.ldef: {self.ldef}")
        linker_flags = self.ldef.parse_flags(flags)
        lib_dirs = [self.ldef.lib_dir(dir) for dir in lib_dirs]
        # In libs, absolute paths are not prepended with the lib prefix (e.g. -l)
        libs = [lib if os.path.isabs(lib) else self.ldef.lib(lib) for lib in libs]
        # The full command.
        cmd = [self.ldef.executable()] + input_paths + libs + linker_flags + lib_dirs + [self.ldef.output(output_path)]
        G_LOGGER.verbose(f"input_paths: {input_paths}, libs: {libs}, linker_flags: {linker_flags}, lib_dirs: {lib_dirs}")
        G_LOGGER.debug(f"Link Command: {' '.join(cmd)}")
        return cmd

    def to_lib(self, name: str) -> str:
        return self.ldef.to_lib(name)

    def to_exec(self, name: str) -> str:
        return self.ldef.to_exec(name)


clang = Linker(ClangDef)
gcc = Linker(GCCDef)
