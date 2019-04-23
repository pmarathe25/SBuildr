from srbuild.graph.node import Node, CompiledNode, LinkedNode
from srbuild.tools.flags import BuildFlags
from srbuild.tools import compiler, linker
from srbuild.project.target import Target
from srbuild.graph.graph import Graph
from typing import List, Union, Dict

# Each profile has a Graph for linked/compiled targets. The source tree (i.e. FileManager) is shared.
# Profiles can have default properties that are applied to each target within.
# TODO: Add compiler/linker as a property of Profile.
class Profile(object):
    def __init__(self, parent: "Project", flags: BuildFlags, build_dir: str):
        self.flags = flags
        self.build_dir = build_dir
        self.parent = parent
        self.graph = Graph()

    # libs can contain either Nodes from this graph, or paths to libraries, or names of libraries
    # TODO(0): Convert Targets in libs to Nodes.
    # This cannot be called with a target_config that has not been
    def target(self, name, source_nodes, flags, libs, compiler, include_dirs, linker, lib_dirs) -> LinkedNode:
        flags = self.flags + target_config.flags
        libs = target_config.libs
        compiler = target_config.compiler
        include_dirs = target_config.include_dirs
        linker = target_config.linker
        lib_dirs = target_config.lib_dirs

        # First, add or retrieve object nodes for each source.
        object_nodes = []
        for source_node in source_nodes:
            # Only the include dirs provided by the user are part of the hash. When the automatically deduced
            # include_dirs change, it means the file is stale, so name collisions don't matter (i.e. OK to overwrite.)
            obj_sig = compiler.signature(source_node.path, include_dirs, flags)
            obj_basename = os.path.basename(os.path.splitext(source_node.path)[0])
            obj_path = os.path.join(self.build_dir, f"{obj_basename}.{obj_sig}.o")
            # User defined includes are always prepended the ones deduced for SourceNodes.
            object_nodes.append(CompiledNode(obj_path, source_node, compiler, include_dirs))

        # For any libraries that are paths or Nodes, treat as inputs.
        # For any libraries that are names, pass them along to the linker.
        # TODO: FIXME: This should respect the order of libs
        input_libs, libs = _process_libs(libs)
        # TODO(0): Node adding for absolute paths should happen in Project, needs to be added to FileManager.
        lib_nodes = [self.graph.add(Node(lib)) for lib in input_libs]

        # Finally, add the actual linked node
        return self._add_linked_node(object_nodes + lib_nodes, flags, linker, libs, lib_dirs)
