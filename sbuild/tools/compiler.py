from sbuild.Logger import G_LOGGER
from typing import List
import subprocess

class Compiler(object):
    def __init__(self, executable="g++"):
        """
        Represents a compiler.

        Args:
            executable (str): The compiler binary to use.
        """
        self.executable = executable

    def signature(self, input_file: str, include_dirs: List[str]=[], opts: List[str]=[]):
        """
        Generates a signature for a given combination of input file and options.
        If the signature is the same for two inputs, it means the resulting object files would be identical.

        Args:
            input_file (str): The path to the input file.

        Optional Args:
            include_dirs (List[str]): A list of paths for include directories.
            opts (List[str]): A list of command-line parameters to pass to the compiler.

        Returns:
            List[str]: A list representing a unique signature for the provided inputs.
        """
        # The signature is everything that makes the resulting object file unique - i.e. compiler, input file, include directories and compile options.
        includes = []
        [includes.extend(["-I", elem]) for elem in include_dirs]
        return [self.executable, input_file] + sorted(opts) + sorted(includes)

    def compile(self, input_file: str, output_file, include_dirs: List[str]=[], opts: List[str]=[]):
        """
        Compiles a single input file to the specified output location.

        Args:
            input_file (str): The path to the input file.
            output_file (str): The path for the output file.

        Optional Args:
            include_dirs (List[str]): A list of paths for include directories.
            opts (List[str]): A list of command-line parameters to pass to the compiler.

        Returns
        """
        sig = self.signature(input_file, include_dirs, opts)
        # The full command, including the output file and the compile-only flag.
        cmd = sig + ["-o", output_file, "-c"]
        G_LOGGER.debug(f"Executing {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
