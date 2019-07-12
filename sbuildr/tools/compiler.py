from sbuildr.tools.flags import BuildFlags
from sbuildr.logger import G_LOGGER
from sbuildr.tools import utils

from typing import List, Union
import copy
import abc

# Responsible for translating sbuildr.tools.flags.BuildFlags to actual command-line flags.
# This class defines everything about each compiler by supplying a unified interface.
# That means that Compiler can blindly use any CompilerDef to generate valid build commands.
class CompilerDef(abc.ABC):
    @staticmethod
    def executable() -> str:
        """
        Specifies executable associated with this CompilerDef.
        For example, this would return "clang" for Clang.

        Returns:
            str: The executable path.
        """
        pass

    @staticmethod
    def compile_only() -> str:
        """
        Specifies compile-only flag for this CompilerDef.
        For example, this would return "-c" for Clang.

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
    def include(path: str) -> str:
        """
        Specifies command-line arguments for adding an include directory.
        For example, this would return "-Ipath" for Clang.

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
class LinuxCompilerDef(CompilerDef):
    @staticmethod
    def compile_only() -> str:
        return "-c"

    @staticmethod
    def output(path: str) -> str:
        return f"-o{path}"

    @staticmethod
    def include(path: str) -> str:
        return f"-I{path}"

    @staticmethod
    def parse_flags(build_flags: BuildFlags) -> List[str]:
        compiler_flags: List[str] = copy.copy(build_flags._raw)
        if build_flags._o:
            compiler_flags.append(f"-O{build_flags._o}")
        if build_flags._std:
            compiler_flags.append(f"-std=c++{build_flags._std}")
        if build_flags._march:
            compiler_flags.append(f"-march={build_flags._march}")
        if build_flags._fpic:
            compiler_flags.append("-fPIC")
        if build_flags._debug:
            compiler_flags.append("-g")
        for define in build_flags._defines:
            compiler_flags.append(f"-D{define}")
        return compiler_flags

class ClangDef(LinuxCompilerDef):
    @staticmethod
    def executable() -> str:
        return "clang"

class GCCDef(LinuxCompilerDef):
    @staticmethod
    def executable() -> str:
        return "gcc"

# Responsible for generating commands that will compile a given source file with the given flags
class Compiler(object):
    def __init__(self, cdef: Union[type, CompilerDef]):
        self.cdef = cdef

    def __str__(self):
        return self.cdef.executable()

    # The signature is everything that makes the resulting object file unique
    # - i.e. compiler, include directories and compile options.
    # If two signatures are the same for an input file, it means the resulting object file(s) would be identical.
    # This helps name object files uniquely, e.g. for release/debug builds.
    def signature(self, input_path: str, include_dirs: List[str]=[], flags: BuildFlags=BuildFlags()) -> str:
        sig = [self.cdef.executable()] + [input_path] + self.cdef.parse_flags(flags) + include_dirs
        return utils.str_hash(sig)

    # Generates the command required to compile the input file with the specified options.
    def compile(self, input_path: str, output_path: str, include_dirs: List[str]=[], flags: BuildFlags=BuildFlags()) -> List[str]:
        compiler_flags = self.cdef.parse_flags(flags)
        includes = [self.cdef.include(dir) for dir in include_dirs]
        # The full command, including the output file and the compile-only flag.
        cmd = [self.cdef.executable(), input_path] + compiler_flags + includes + [self.cdef.compile_only(), self.cdef.output(output_path)]
        G_LOGGER.verbose(f"Compile Command: {' '.join(cmd)}")
        return cmd

clang = Compiler(ClangDef)
gcc = Compiler(GCCDef)
