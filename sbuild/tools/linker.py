from sbuild.tools.language import Language
from sbuild.logger import G_LOGGER
import sbuild.utils as utils
from typing import List, Dict, Set
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
            flags (Dict[Flags, str]): A mapping of Flags to their respective command-line strings.
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

    def signature(self, link_dirs: Set[str]=[], opts: Set[str]=[], language=Language.CPP, shared=False) -> List[str]:
        """
        Generates a signature for a given combination of input file and options.
        If two signatures are the same for an input file, it means the resulting file(s) would be identical.

        Args:
            input_files (Set[str]): A set of paths to the input object files.

        Optional Args:
            link_dirs (Set[str]): A set of paths for link directories.
            opts (Set[str]): A set of command-line parameters to pass to the linker.

        Returns:
            str: A unique signature for the provided inputs.
        """
        # The signature is everything that makes the resulting object file unique - i.e. linker, input file, link directories and linker options.
        link_dirs = set([os.path.realpath(dir) for dir in link_dirs])
        sig = sorted(set([self.executable]) | opts | link_dirs | set([str(language), str(shared)]))
        return utils.str_hash(sig)

    def link(self, input_files: Set[str], output_file, link_dirs: Set[str]=[], opts: Set[str]=[], language=Language.CPP, shared=False):
        """
        Links the provided input files into.

        Args:
            input_files (Set[str]): A set of paths to the input object files.
            output_file (str): The path for the output file.

        Optional Args:
            link_dirs (Set[str]): A set of paths for link directories.
            opts (Set[str]): A set of command-line parameters to pass to the linker.
            language (sbuild.tools.language.Language): The language to use for the input files.
            shared (bool): If True, link the inputs into a shared library, otherwise, into an executable.

        Returns
        """
        # Add shared flag if needed.
        extra_opts = set([self.flags[Flags.SHARED]] if shared else [])
        if language is Language.CPP:
            extra_opts.add(self.libcpp)
        # Set up link dirs.
        links = []
        [links.extend([self.flags[Flags.LINK_DIR], elem]) for elem in link_dirs]
        # The full command.
        cmd = [self.executable] + list(input_files) + list(opts | extra_opts) + links + [self.flags[Flags.OUTPUT], output_file]
        # Execute.
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
