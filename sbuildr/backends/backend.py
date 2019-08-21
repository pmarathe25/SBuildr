from sbuildr.graph.node import Node, CompiledNode, LinkedNode
from sbuildr.graph.graph import Graph
from sbuildr.logger import G_LOGGER

from typing import List, Dict
import subprocess

class Backend(object):
    # Generate a build command for the given node.
    # For source nodes and basic nodes this is an empty list, otherwise, it is a compiler/linker command.
    def _node_command(self, node: Node) -> List[str]:
        if isinstance(node, CompiledNode):
            source = node.inputs[0]
            # The CompiledNode's include dirs take precedence over the SourceNode's. The ones in the SourceNode are
            # automatically deduced, whereas the ones in the CompiledNode are provided by the user.
            return node.compiler.compile(source.path, node.path, node.include_dirs + source.include_dirs, node.flags)
        elif isinstance(node, LinkedNode):
            # Only link CompiledNodes. All libraries should come from node.libs
            return node.linker.link([inp.path for inp in node.inputs if isinstance(inp, CompiledNode)], node.path, node.libs, node.lib_dirs, node.flags)
        return []

    def __init__(self, build_dir: str):
        """
        A backend that creates build configuration files for a project, and is able to build arbitrary targets specified in the project. Intermediate build configuration files will be written to the build directory specified by the project's FileManager.

        :param build_dir: A directory in which intermediate configuration files can be written.
        """
        self.build_dir = build_dir

    def configure(self, build_graph: Graph):
        """
        Generates build configuration files based on the source files provided by the project's file manager,
        and targets specified in each profile.

        :param build_graph: A graph of the source files and profile targets in the project.

        :returns: The generated build file.
        """
        raise NotImplementedError()

    def build(self, nodes: List[Node]) -> (subprocess.CompletedProcess, float):
        """
        Runs a build command that will generate the specified nodes.

        :param nodes: The nodes to build.

        :returns: :class:`Tuple[subprocess.CompletedProcess, float]` The return code of the build command and the time required to execute the build command.
        """
        raise NotImplementedError()
