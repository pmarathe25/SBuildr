from srbuild.project.file_manager import FileManager
from srbuild.tools.compiler import Compiler
from srbuild.tools.linker import Linker
from srbuild.tools.flags import BuildFlags
from srbuild.graph.graph import Graph
from srbuild.graph.node import Node
from srbuild.logger import G_LOGGER
from typing import List, Set, Union, Dict
import inspect
import os

class Target(dict):
    pass

# Each profile has a Graph for linked/compiled targets. The source tree (i.e. FileManager) is shared.
# Profiles can have default properties that are applied to each target within.
class Profile(object):
    def __init__(self, parent: "Project", flags: BuildFlags, build_dir: str):
        self.flags = flags
        self.build_dir = build_dir
        self.parent = parent
        self.graph = Graph()

    # libs can contain either Nodes from this graph, or paths to libraries, or names of libraries
    def add_linked_target(self, name: str, sources: List[str], flags: BuildFlags, libs: List[Union[Node, str]], compiler: Compiler, include_dirs: List[str], linker: Linker, lib_dirs: List[str]) -> Node:
        # TODO: Factor out common code from here into Project.
        # First, add or retrieve object nodes for each source.
        object_nodes = []
        for source in sources:
            # Get the absolute path of this source file, then query the file manager.
            source_path = _source_path(source)
            source_node, source_include_dirs = self.parent.files.source_info(source_path)
            # User defined includes are always prepended.
            object_nodes.append(_add_object_node(source_node, flags, compiler, include_dirs + source_include_dirs))

        # TODO: Linker needs to handle libraries.
        # For any libraries that are paths or Nodes, treat as inputs.
        # For any libraries that are names, pass them along to the linker.
        # TODO: FIXME: This should respect the order of libs
        input_libs, libs = _process_libs(libs)
        lib_nodes = [self.graph.add(Node(lib)) for lib in input_libs]

        # Finally, add the actual linked node
        return self._add_linked_node(object_nodes + lib_nodes, flags, linker, libs, lib_dirs)

class Project(object):
    def __init__(self, root: str="", dirs: Set[str]=set(), build_dir: str=""):
        """
        Represents a project.

        Vars:
            dirs (Set[str]): The directories that are part of the project.
        """
        # The assumption is that the caller of the init function is the SRBuild file for the build.
        # TODO: Make this walk all the way up the stack to the top-level caller.
        self.root_dir = root if root else os.path.abspath(os.path.dirname(inspect.stack()[1][0].f_code.co_filename))
        self.build_dir = os.path.abspath(build_dir) if build_dir else os.path.join(self.root_dir, "build")
        self.dirs = set(map(os.path.abspath, dirs)) if dirs else set([self.root_dir])
        G_LOGGER.debug(f"Using Root: {self.root_dir}, Build: {self.build_dir}, Dirs: {self.dirs}")
        # Keep track of all files present in project dirs. Since dirs is a set,
        # files is guaranteed to contain no duplicates as well.
        self.files = FileManager(self.dirs)
        self.profiles: Dict[str, Profile] = {}
        # Add default profiles
        self.profile(name="release", flags=BuildFlags().O(3).std(17).march("native").fpic())
        self.profile(name="debug", flags=BuildFlags().O(0).std(17).debug().fpic())

    def _target_impl(self, name: str, sources: List[str], flags: BuildFlags, libs: List[Union[Target, str]], compiler: Compiler, include_dirs: List[str], linker: Linker, lib_dirs: List[str]) -> Target:
        target = Target()
        for name, profile in self.profiles.items():
            # TODO: Convert Targets in libs to Nodes.
            target[name] = profile.add_linked_target(name, sources, libs, flags, compiler, include_dirs, linker, lib_dirs)
        return target

    # TODO: Docstrings
    # These functions return per-profile nodes
    def executable(self, name, sources, libs, flags, compiler, include_dirs, linker, lib_dirs) -> Target:
        return self._target_impl(name, sources, libs, flags, compiler, include_dirs, linker, lib_dirs)

    def library(self, name, sources, libs, flags, compiler, include_dirs, linker, lib_dirs) -> Target:
        return self._target_impl(name, sources, libs, flags + BuildFlags().shared(), compiler, include_dirs, linker, lib_dirs)

    # Returns a profile if it exists, otherwise creates a new one and returns it.
    # If the profile does
    def profile(self, name, flags: BuildFlags=BuildFlags(), build_subdir: str=None) -> Profile:
        if name not in self.profiles:
            build_subdir = build_subdir or name
            build_dir = os.path.join(self.build_dir, build_subdir)
            self.profiles[name] = Profile(parent=self, flags=flags, build_dir=build_dir)
        return self.profiles[name]
