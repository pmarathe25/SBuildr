from srbuild.project.file_manager import FileManager
from srbuild.tools.compiler import Compiler
from srbuild.tools.linker import Linker
from srbuild.tools.flags import BuildFlags
from srbuild.graph.graph import Graph
from srbuild.graph.node import Node
from srbuild.logger import G_LOGGER
from typing import List, Set, Union
import inspect
import os

class Project(object):
    def __init__(self, root: str="", dirs: Set[str]=set(), build: str=""):
        """
        Represents a project.

        Vars:
            dirs (Set[str]): The directories that are part of the project.
        """
        # The assumption is that the caller of the init function is the SRBuild file for the build.
        # TODO: Make this walk all the way up the stack to the top-level caller.
        self.root_dir = root if root else os.path.abspath(os.path.dirname(inspect.stack()[1][0].f_code.co_filename))
        self.build = os.path.abspath(build) if build else os.path.join(self.root_dir, "build")
        self.dirs = set(map(os.path.abspath, dirs)) if dirs else set([self.root_dir])
        G_LOGGER.debug(f"Using Root: {self.root_dir}, Build: {self.build}, Dirs: {self.dirs}")
        # Keep track of all files present in project dirs. Since dirs is a set,
        # files is guaranteed to contain no duplicates as well.
        self.files = FileManager(self.dirs)
        self.graph = Graph()

    # libs can contain either Nodes from this graph, or paths to libraries, or names of libraries
    def _target_impl(self, name: str, sources: List[str], flags: BuildFlags, libs: List[Union[Node, str]], compiler: Compiler, include_dirs: List[str], linker: Linker, lib_dirs: List[str]) -> Node:
        # First add or retrieve object nodes for each source.
        pass 

    # TODO: Docstrings
    def executable(self, name, sources, libs, flags, compiler, include_dirs, linker, lib_dirs) -> Node:
        return self._target_impl(name, sources, libs, flags, compiler, include_dirs, linker, lib_dirs)

    def library(self, name, sources, libs, flags, compiler, include_dirs, linker, lib_dirs) -> Node:
        return self._target_impl(name, sources, libs, flags + BuildFlags().shared(), compiler, include_dirs, linker, lib_dirs)
