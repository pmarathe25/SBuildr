from sbuildr.graph.node import Node, CompiledNode, LinkedNode
from sbuildr.graph.graph import Graph
from sbuildr.logger import G_LOGGER

from typing import List, Dict
import subprocess

class Backend(object):
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
