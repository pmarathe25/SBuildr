from sbuild.logger import G_LOGGER
from sbuild.tools.language import Language
from typing import List, Dict
import subprocess
import enum
import os

class Flags(enum.Flag):
    SHARED = 1
    OUTPUT = 2
    LINK_DIR = 3
    LIBRARY_PREFIX = 4

class Linker(object):
    def __init__(self, executable, flags: Dict[Flags, str]):
        """
        Represents a linker.

        Args:
            executable (str): The linker binary to use.
        """
        def find_libcpp():
            # Prefer libc++, but fall back to libstdc++ if needed.
            try:
                subprocess.run([self.executable, self.flags[Flags.LIBRARY_PREFIX] + "c++", self.flags[Flags.OUTPUT], os.devnull], check=True, capture_output=True)
                return self.flags[Flags.LIBRARY_PREFIX] + "c++"
            except subprocess.CalledProcessError:
                G_LOGGER.debug("Could not find libc++, falling back to libstdc++")
                return self.flags[Flags.LIBRARY_PREFIX] + "stdc++"

        self.executable = executable
        self.flags = flags
        self.libcpp = find_libcpp()

    def signature(self, input_files: List[str], link_dirs: List[str]=[], opts: List[str]=[]):
        """
        Generates a signature for a given combination of input file and options.
        If the signature is the same for two inputs, it means the resulting object files would be identical.

        Args:
            input_files (List[str]): A list of paths to the input object files.

        Optional Args:
            link_dirs (List[str]): A list of paths for link directories.
            opts (List[str]): A list of command-line parameters to pass to the linker.

        Returns:
            List[str]: A list representing a unique signature for the provided inputs.
        """
        # The signature is everything that makes the resulting object file unique - i.e. linker, input file, link directories and compile options.
        includes = []
        [includes.extend([self.flags[Flags.LINK_DIR], elem]) for elem in link_dirs]
        return [self.executable] + input_files + sorted(opts) + sorted(includes)

    def link(self, input_files: List[str], output_file, link_dirs: List[str]=[], opts: List[str]=[], language=Language.CPP, shared=False):
        """
        Links the provided input files into.

        Args:
            input_files (List[str]): A list of paths to the input object files.
            output_file (str): The path for the output file.

        Optional Args:
            link_dirs (List[str]): A list of paths for link directories.
            opts (List[str]): A list of command-line parameters to pass to the linker.
            language (sbuild.tools.language.Language): The language to use for the input files.
            shared (bool): If True, link the inputs into a shared library, otherwise, into an executable.

        Returns
        """
        extra_opts = [self.flags[Flags.SHARED]] if shared else []
        if language is Language.CPP:
            extra_opts.append(self.libcpp)
        sig = self.signature(input_files, link_dirs, opts + extra_opts)
        # The full command.
        cmd = sig + [self.flags[Flags.OUTPUT], output_file]
        G_LOGGER.info(f"Linking {output_file}")
        G_LOGGER.debug(f"Executing: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.stdout:
            G_LOGGER.info(f"\n{proc.stdout}")
        if proc.stderr:
            G_LOGGER.error(f"\n{proc.stderr}")

# Default linkers
clang = Linker("clang", flags={Flags.SHARED: "-shared", Flags.OUTPUT: "-o", Flags.LINK_DIR: "-L", Flags.LIBRARY_PREFIX: "-l"})
gcc = Linker("gcc", flags={Flags.SHARED: "-shared", Flags.OUTPUT: "-o", Flags.LINK_DIR: "-L", Flags.LIBRARY_PREFIX: "-l"})
