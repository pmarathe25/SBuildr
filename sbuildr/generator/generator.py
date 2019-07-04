from sbuildr.graph.node import Node, CompiledNode, LinkedNode
from sbuildr.project.project import Project
from sbuildr.project.target import ProjectTarget
from sbuildr.logger import G_LOGGER

from typing import List, Dict
import subprocess

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

    def __init__(self, project: Project):
        """
        A generator that creates build files for the specified project, and is able to build arbitrary targets specified in the project. Intermediate build configuration files will be written to the build directory specified by the project's FileManager.

        Args:
            :param project: The project managed by this generator.
        """
        self.project = project

    def generate(self):
        """
        Generates build configuration files based on the source files provided by the project's file manager,
        and targets specified in each profile.

        Side Effects:
            This function will invoke the managed project's `prepare_for_build` function, which may affect its state.
            It will also invoke the project's file manager's mkdir function to create the build directory if it does not exist.

        Returns:
            str: The generated build file.
        """
        raise NotImplementedError()

    def needs_configure(self) -> bool:
        """
        Whether the project needs to be configured using this generator. If this returns False, it means the project is ready to build.

        Returns:
            bool: Whether the project needs to be configured using this generator before building.
        """
        raise NotImplementedError()

    def build(self, targets: List[ProjectTarget], profiles: List[str]=[]) -> (subprocess.CompletedProcess, float):
        """
        Runs a build command that will generate the specified targets from the specified profiles.

        Side Effects:
            This function will invoke the managed project's file manager's mkdir function to create the build subdirectory for each profile if it does not exist.

        Args:
            :param targets: The targets to build.
            :param profiles: The names of the profiles to build for. If no profiles are provided, builds the specified targets for all profiles. If a target does not exist for one of the specified profiles, that target is skipped for that profile.

        :returns: :class:`Tuple[subprocess.CompletedProcess, float]` The return code of the build command and the time required to execute the build command.
        """
        raise NotImplementedError()
