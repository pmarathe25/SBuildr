from srbuild.project.file_manager import FileManager
from srbuild.tools.flags import BuildFlags
from srbuild.graph.graph import Graph
from srbuild.logger import G_LOGGER
from typing import Set
import inspect
import os

global DEFAULT_GRAPH
DEFAULT_GRAPH = Graph()

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

    def _target_impl(self, name, sources, flags, compiler, linker, include_dirs, lib_dirs):
        pass

    def executable(self, name, sources, flags, compiler, linker, include_dirs, lib_dirs):
        return self._target_impl(name, sources, flags + BuildFlags().shared(), compiler, linker, include_dirs, lib_dirs)

    def library(self, name, sources, flags, compiler, linker, include_dirs, lib_dirs):
        return self._target_impl(name, sources, flags + BuildFlags().shared(), compiler, linker, include_dirs, lib_dirs)
