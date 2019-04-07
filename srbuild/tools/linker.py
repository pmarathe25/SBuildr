from srbuild.tools.flags import BuildFlags
from srbuild.logger import G_LOGGER
import srbuild.utils as utils
from typing import List, Dict

# TODO: Use ldconfig to locate libraries, and get libstdc++ out of here.
# Responsible for generating commands that will link the given source files into a shared library or executable.
class Linker(object):
    def __init__(self, executable, shared_flag, output_flag, link_dir_flag, lib_prefix, flag_map: Dict[BuildFlags, str]={}):
        self.executable = executable
        self.shared_flag = shared_flag
        self.output_flag = output_flag
        self.link_dir_flag = link_dir_flag
        self.lib_prefix = lib_prefix
        self.flag_map = flag_map

    # Generates a signature for a given combination of input file and options.
    # If two signatures are the same for an input file, it means the resulting file(s) would be identical.
    # The signature is everything that makes the resulting object file unique - i.e. linker, input file, link directories and linker options.
    def signature(self, link_dirs: List[str]=[], opts: List[BuildFlags]=[], shared=False) -> List[str]:
        sig = [self.executable] + opts + link_dirs + [str(shared)]
        return utils.str_hash(sig)

    # Generates the command required to link the inputs files with the specified options.
    def link(self, input_files: List[str], output_file, link_dirs: List[str]=[], opts: List[BuildFlags]=[], shared=False):
        # Convert opts to their actual values.
        opts = [self.flag_map[opt] for opt in opts]
        # Add shared flag if needed.
        if shared:
            opts.append(self.shared_flag)
        links = []
        [links.extend([self.link_dir_flag, elem]) for elem in link_dirs]
        # The full command.
        cmd = [self.executable] + list(input_files) + list(opts | extra_opts) + links + [self.flags[LFlags.OUTPUT], output_file]
        G_LOGGER.debug(f"Link Command: {' '.join(cmd)}")
        return cmd

# Default linkers
# clang = Linker("clang", flags={LFlags.SHARED: "-shared", LFlags.OUTPUT: "-o", LFlags.LINK_DIR: "-L", LFlags.LIBRARY_PREFIX: "-l"})
# gcc = Linker("gcc", flags={LFlags.SHARED: "-shared", LFlags.OUTPUT: "-o", LFlags.LINK_DIR: "-L", LFlags.LIBRARY_PREFIX: "-l"})
