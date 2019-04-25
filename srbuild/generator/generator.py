from srbuild.graph.node import Node, CompiledNode, LinkedNode
from srbuild.project.project import Project
from srbuild.logger import G_LOGGER

from typing import List

class Generator(object):
    # Generate a build command for the given node.
    # For source nodes and basic nodes this is an empty list, otherwise, it is a compiler/linker command.
    def _node_command(self, node: Node) -> List[str]:
        if isinstance(node, CompiledNode):
            if len(node.inputs) != 1:
                G_LOGGER.critical(f"CompiledNodes must have exactly one inputs, but received {node} with inputs: {node.inputs}")
            source = node.inputs[0]
            # The CompiledNode's include dirs take precedence over the SourceNode's. The ones in the SourceNode are
            # automatically deduced, whereas the ones in the CompiledNode are provided by the user.
            return node.compiler.compile(source.path, node.path, node.include_dirs + source.include_dirs, node.flags)
        elif isinstance(node, LinkedNode):
            return node.linker.link([inp.path for inp in node.inputs], node.path, node.libs, node.lib_dirs, node.flags)
        return []

    def generate(self, project: Project) -> str:
        """
        Generates a configuration file based on the source files provided by the project's file manager,
        and targets specified in each profile.

        Args:
            project (Project): The project for which to generate build file. This should contain:
                The file manager that describes all the source files of the project. files.graph should be populated and accessible.
                Profiles, where each profile contains zero or more build targets. profile.graph should be populated and accessible for each profile.

        Returns:
            str: The generated build file.
        """
        raise NotImplementedError()

    def build_command(self, config_path: str, targets: List[LinkedNode]) -> List[str]:
        """
        Returns a build command that can be run on the command line to build the specified target paths.

        Args:
            config_path (str): The path to the config file that was generated.
            targets (List[LinkedNode]): The nodes for the targets that should be built.
        """
        raise NotImplementedError()
