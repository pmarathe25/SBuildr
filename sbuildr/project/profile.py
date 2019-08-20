from sbuildr.tools.flags import BuildFlags
from sbuildr.graph.node import Library
from sbuildr.graph.graph import Graph
from sbuildr.logger import G_LOGGER

from typing import List, Union, Dict
import copy
import os

# Inserts suffix into path, just before the extension
def _file_suffix(path: str, suffix: str, ext: str = None) -> str:
    split = os.path.splitext(os.path.basename(path))
    basename = split[0]
    ext = ext or split[1]
    suffixed = f"{basename}{suffix}{(ext if ext else '')}"
    G_LOGGER.verbose(f"_file_suffix received path: {path}, split into {split}. Using suffix: {suffix}, generated final name: {suffixed}")
    return suffixed

# Each profile has a Graph for linked/compiled targets. The source tree (i.e. FileManager) is shared.
# Profiles can have default properties that are applied to each target within.
# TODO: Add compiler/linker as a property of Profile.
class Profile(object):
    """
    Represents a profile in a project. A profile is essentially a set of options applied to targets in the project.
    For example, a profile can be used to specify that all targets should be built with debug information, and that they should have a "_debug" suffix.

    :param flags: The flags to use for this profile. These will be applied to all targets for this profile. Per-target flags always take precedence.
    :param build_dir: An absolute path to the build directory to use.
    :param suffix: A file suffix to attach to all artifacts generated for this profile.
    """
    def __init__(self, flags: BuildFlags, build_dir: str, suffix: str):
        self.flags = flags
        self.build_dir = build_dir
        self.graph = Graph()
        self.suffix = suffix


    # Propagates library dirs from dependencies to their dependees.
    def configure_libraries(self):
        for layer in self.graph.layers():
            lib_nodes = [node for node in layer if isinstance(node, Library)]
            for node in lib_nodes:
                # Pull in libraries from this node's inputs
                lib_inputs = [inp for inp in node.inputs if isinstance(inp, Library)]
                for inp in lib_inputs:
                    # Avoid duplicates in libs/lib_dirs.
                    if inp.name not in node.libs:
                        node.libs.append(inp.name)
                        node.libs.extend(inp.libs)
                        # Add the dependency's lib_dirs in addition to the directory containing the dependency itself.
                        lib_dirs = ([os.path.dirname(inp.path)] if inp.path else []) + inp.lib_dirs
                        lib_dirs = [dir for dir in lib_dirs if dir not in node.lib_dirs]
                        node.lib_dirs.extend(lib_dirs)
                        G_LOGGER.verbose(f"Adding library: {inp.name}, and library directories: {lib_dirs} to {node}")
                    # Lastly, if this input does not have a path, it needs to be removed
                    if not inp.path:
                        node.remove_input(inp)
