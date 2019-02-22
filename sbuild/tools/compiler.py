from sbuild.logger import G_LOGGER
import sbuild.utils as utils
from typing import List, Dict, Set
import subprocess
import enum
import os

class Flags(enum.Flag):
    COMPILE_ONLY = 1
    OUTPUT = 2
    INCLUDE_DIR = 3

class Compiler(object):
    def __init__(self, executable, flags: Dict[Flags, str]):
        """
        Represents a compiler.

        Args:
            executable (str): The compiler binary to use.
            flags (Dict[Flags, str]): A mapping of Flags to their respective command-line strings.
        """
        self.executable = executable
        self.flags = flags

    def signature(self, opts: Set[str]=[]) -> str:
        """
        Generates a signature for a given set of options.
        If two signatures are the same for an input file, it means the resulting object file(s) would be identical.

        Optional Args:
            include_dirs (Set[str]): A set of paths for include directories.
            opts (Set[str]): A set of command-line parameters to pass to the compiler.

        Returns:
            str: A unique signature for the provided inputs.
        """
        # The signature is everything that makes the resulting object file unique - i.e. compiler, input file, include directories and compile options.
        sig = sorted(set([self.executable]) | opts)
        return utils.str_hash(sig)

    def compile(self, input_file: str, output_file, include_dirs: Set[str]=[], opts: Set[str]=[]):
        """
        Compiles a single input file to the specified output location.

        Args:
            input_file (str): The path to the input file.
            output_file (str): The path for the output file.

        Optional Args:
            include_dirs (Set[str]): A set of paths for include directories.
            opts (Set[str]): A set of command-line parameters to pass to the compiler.

        Returns
        """
        includes = []
        [includes.extend([self.flags[Flags.INCLUDE_DIR], elem]) for elem in include_dirs]
        # The full command, including the output file and the compile-only flag.
        cmd = [self.executable, input_file] + list(opts) + includes + [self.flags[Flags.COMPILE_ONLY], self.flags[Flags.OUTPUT], output_file]
        # Execute
        G_LOGGER.info(f"Compiling {output_file}")
        G_LOGGER.debug(f"Executing: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.stdout:
            G_LOGGER.info(f"\n{proc.stdout}")
        if proc.stderr:
            G_LOGGER.error(f"\n{proc.stderr}")

# Default compilers
clang = Compiler("clang", flags={Flags.COMPILE_ONLY: "-c", Flags.OUTPUT: "-o", Flags.INCLUDE_DIR: "-I"})
gcc = Compiler("gcc", flags={Flags.COMPILE_ONLY: "-c", Flags.OUTPUT: "-o", Flags.INCLUDE_DIR: "-I"})
