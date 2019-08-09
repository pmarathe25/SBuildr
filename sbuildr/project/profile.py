from sbuildr.graph.node import Node, CompiledNode, LinkedNode
from sbuildr.tools.flags import BuildFlags
from sbuildr.graph.graph import Graph
from sbuildr.logger import G_LOGGER
from sbuildr.misc import paths

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
    def __init__(self, flags: BuildFlags, build_dir: str, common_objs_build_dir:str, suffix: str):
        self.flags = flags
        self.build_dir = build_dir
        self.common_objs_build_dir = common_objs_build_dir
        self.graph = Graph()
        self.suffix = suffix

    # libs can contain either Nodes from this graph, or paths to libraries, or names of libraries
    def target(self, basename, source_nodes, flags, libs: List[Union[Node, str]], compiler, include_dirs, linker, lib_dirs) -> LinkedNode:
        # Per-target flags always overwrite profile flags.
        flags = self.flags + flags

        # First, add or retrieve object nodes for each source.
        input_nodes = []
        for source_node in source_nodes:
            # Only the include dirs provided by the user are part of the hash. When the automatically deduced
            # include_dirs change, it means the file is stale, so name collisions don't matter (i.e. OK to overwrite.)
            obj_sig = compiler.signature(source_node.path, include_dirs, flags)
            obj_path = os.path.join(self.common_objs_build_dir, _file_suffix(source_node.path, f".{obj_sig}", ".o"))
            # User defined includes are always prepended the ones deduced for SourceNodes.
            obj_node = CompiledNode(obj_path, source_node, compiler, include_dirs, flags)
            input_nodes.append(self.graph.add(obj_node))

        # For any libraries that are Nodes, add to lib_names and lib_dirs, otherwise, just add to lib_names
        # Nodes are also added to the LinkedNodes inputs, for timestamp checks during the build.
        lib_names: List[str] = []
        local_lib_dirs = copy.deepcopy(lib_dirs)
        for lib in libs:
            if isinstance(lib, Node):
                input_nodes.append(lib)
                lib_names.append(paths.libname_to_name(os.path.basename(lib.path)))
                local_lib_dirs.append(os.path.dirname(lib.path))
            else:
                lib_names.append(lib)
        G_LOGGER.verbose(f"Final libraries: {lib_names}, and library directories: {local_lib_dirs}")

        # Finally, add the actual linked node
        linked_path = os.path.join(self.build_dir, _file_suffix(basename, self.suffix))
        linked_node = LinkedNode(linked_path, input_nodes, linker, lib_names, local_lib_dirs, flags)
        return self.graph.add(linked_node)
