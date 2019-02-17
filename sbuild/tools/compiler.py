from typing import List
from sbuild.Logger import G_LOGGER

class Compiler(object):
    def __init__(self, executable="g++"):
        """
        Represents a compiler.

        Args:
            executable (str): The compiler binary to use.
        """
        self.executable = executable

    def signature(self, input_file: str, opts: List[str]=[]):
        """
        Generates a signature for a given combination of input file and options.
        If the signature is the same for two inputs, it means the resulting object files would be identical.

        Args:
            input_file (str): The path to the input file. Must be convertible to an absolute path.

        Optional Args:
            opts (List[str]): A list of command-line parameters to pass to the compiler.

        Returns:
            List[str]: A list representing a unique signature for the provided inputs.
        """
        # The signature is everything that makes the resulting object file unique - i.e. compiler, input file and options.
        return [self.executable, input_file] + sorted(opts)

    def compile(self, input_file: str, output_file, opts: List[str]=[]):
        """
        Compiles a single input file to the specified output location.

        Args:
            input_file (str): The path to the input file. Must be convertible to an absolute path.
            output_file (str): The path for the output file.

        Optional Args:
            opts (List[str]): A list of command-line parameters to pass to the compiler.

        Returns
        """
        sig = self.signature(input_file, opts)
        # The full command, including the output file.
        cmd = sig + ["-o", output_file]
        subprocess.run(cmd, check=True)
