from srbuild.graph.node import CompiledNode, LinkedNode
from srbuild.project.file_manager import FileManager
from srbuild.project.profile import Profile
from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from srbuild.project.target import Target
from srbuild.graph.graph import Graph
from srbuild.logger import G_LOGGER
from typing import List, Set, Union, Dict, Tuple
from collections import OrderedDict
import inspect
import os

class Project(object):
    def __init__(self, root: str="", dirs: Set[str]=set(), build_dir: str=""):
        """
        Represents a project.

        Vars:
            dirs (Set[str]): The directories that are part of the project.
        """
        # The assumption is that the caller of the init function is the SRBuild file for the build.
        root_dir = root if root else os.path.abspath(os.path.dirname(inspect.stack()[1][0].f_code.co_filename))
        # Keep track of all files present in project dirs. Since dirs is a set, files is guaranteed
        # to contain no duplicates as well.
        self.files = FileManager(root_dir, build_dir, dirs)
        self.executables: Dict[str, Target] = {}
        self.libraries: Dict[str, Target] = {}
        self.profiles: Dict[str, Profile] = {}
        # Add default profiles
        self.profile(name="release", flags=BuildFlags().O(3).std(17).march("native").fpic())
        self.profile(name="debug", flags=BuildFlags().O(0).std(17).debug().fpic())

    def _get_source_nodes(self, sources) -> List[CompiledNode]:
        # Convert sources to full paths
        source_nodes: List[CompiledNode] = [self.files.source(path) for path in sources]
        G_LOGGER.verbose(f"For sources: {sources}, found source paths: {source_nodes}")
        return source_nodes

    # TODO: Docstrings
    def executable(self,
                    name: str,
                    sources: List[str],
                    flags: BuildFlags = BuildFlags(),
                    libs: List[Union[Target, str]] = [],
                    compiler: compiler.Compiler = compiler.clang,
                    include_dirs: List[str] = [],
                    linker: linker.Linker = linker.clang,
                    lib_dirs: List[str] = []) -> Target:
        source_nodes = self._get_source_nodes(sources)
        self.executables[name] = Target()
        for profile_name, profile in self.profiles.items():
            self.executables[name][profile_name] = profile.target(name, source_nodes, flags, libs, compiler, include_dirs, linker, lib_dirs)
        return self.executables[name]

    def library(self,
                name: str,
                sources: List[str],
                flags: BuildFlags = BuildFlags(),
                libs: List[Union[Target, str]] = [],
                compiler: compiler.Compiler = compiler.clang,
                include_dirs: List[str] = [],
                linker: linker.Linker = linker.clang,
                lib_dirs: List[str] = []) -> Target:
        source_nodes = self._get_source_nodes(sources)
        self.libraries[name] = Target()
        for profile_name, profile in self.profiles.items():
            self.libraries[name][profile_name] = profile.target(name, source_nodes, flags + BuildFlags().shared(), libs, compiler, include_dirs, linker, lib_dirs)
        return self.libraries[name]

    # Before configuring, populate the source field of None
    def configure(self) -> None:
        pass

    # Returns a profile if it exists, otherwise creates a new one and returns it.
    def profile(self, name, flags: BuildFlags=BuildFlags(), build_subdir: str=None) -> Profile:
        if name not in self.profiles:
            build_subdir = build_subdir or name
            build_dir = os.path.join(self.files.build_dir, build_subdir)
            self.profiles[name] = Profile(parent=self, flags=flags, build_dir=build_dir)
        return self.profiles[name]
