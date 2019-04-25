from srbuild.graph.node import Node, CompiledNode, LinkedNode
from srbuild.project.file_manager import FileManager
from srbuild.project.profile import Profile
from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from srbuild.project.target import ProjectTarget
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
        self.executables: Dict[str, ProjectTarget] = {}
        self.libraries: Dict[str, ProjectTarget] = {}
        self.profiles: Dict[str, Profile] = {}
        # Add default profiles
        self.profile(name="release", flags=BuildFlags().O(3).std(17).march("native").fpic())
        self.profile(name="debug", flags=BuildFlags().O(0).std(17).debug().fpic())
        # Whether this project has been configured for building.
        self.configured = False

    def _target(self, basename: str, sources: List[str], flags: BuildFlags, libs: List[Union[ProjectTarget, str]], compiler: compiler.Compiler, include_dirs: List[str], linker: linker.Linker, lib_dirs: List[str]) -> ProjectTarget:

        # Convert sources to full paths
        def get_source_nodes(sources: List[str]) -> List[CompiledNode]:
            source_nodes: List[CompiledNode] = [self.files.source(path) for path in sources]
            G_LOGGER.verbose(f"For sources: {sources}, found source paths: {source_nodes}")
            return source_nodes

        # The linker expects libs to be either absolute paths, or library names.
        # e.g. ["stdc++", "/path/to/libtest.so"]
        # If the library is provided as a path, we also add it as a node to the file manager
        # so that we can properly rebuild when it is updated (even if it's external).
        def get_libraries(libs: List[Union[ProjectTarget, str]]) -> List[Union[ProjectTarget, Node, str]]:

            # Determines whether lib looks like a path, or like a library name.
            def is_lib_path(lib: str) -> bool:
                has_path_components = os.path.sep in lib
                has_ext = bool(os.path.splitext(lib)[1])
                return has_path_components or has_ext

            fixed_libs = []
            for lib in libs:
                # Targets are handled by each profile individually
                if not isinstance(lib, ProjectTarget):
                    candidates = self.files.find(lib)
                    if is_lib_path(lib):
                        if len(candidates) > 1:
                            G_LOGGER.warning(f"For library: {lib}, found multiple candidates: {candidates}. Using {candidates[0]}. If this is incorrect, please provide a longer path to disambiguate.")
                        # Add the library to the file manager as an external path
                        lib = self.files.external(lib)
                    elif candidates:
                        G_LOGGER.warning(f"For library: {lib}, found matching paths: {candidates}. However, {lib} appears to be a library name rather than a path to a library. If you meant to use the path, please provide a longer path to disambiguate.")
                fixed_libs.append(lib)
            G_LOGGER.debug(f"Using fixed libs: {fixed_libs}")
            return fixed_libs

        source_nodes = get_source_nodes(sources)
        libs: List[Union[ProjectTarget, Node, str]] = get_libraries(libs)
        target = ProjectTarget()
        for profile_name, profile in self.profiles.items():
            # Process targets so we only give each profile its own LinkedNodes.
            # Purposely don't convert all libs to paths here, so that each profile can set up dependencies correctly.
            target_libs = [lib if not isinstance(lib, ProjectTarget) else lib[profile_name] for lib in libs]
            target[profile_name] = profile.target(basename, source_nodes, flags, target_libs, compiler, include_dirs, linker, lib_dirs)
        return target

    # TODO: Docstrings
    # Both of these functions will modify name before passing it to profile so that the filename is correct.
    def executable(self,
                    name: str,
                    sources: List[str],
                    flags: BuildFlags = BuildFlags(),
                    libs: List[Union[ProjectTarget, str]] = [],
                    compiler: compiler.Compiler = compiler.clang,
                    include_dirs: List[str] = [],
                    linker: linker.Linker = linker.clang,
                    lib_dirs: List[str] = []) -> ProjectTarget:
        self.executables[name] = self._target(linker.to_exec(name), sources, flags, libs, compiler, include_dirs, linker, lib_dirs)
        return self.executables[name]

    def library(self,
                name: str,
                sources: List[str],
                flags: BuildFlags = BuildFlags(),
                libs: List[Union[ProjectTarget, str]] = [],
                compiler: compiler.Compiler = compiler.clang,
                include_dirs: List[str] = [],
                linker: linker.Linker = linker.clang,
                lib_dirs: List[str] = []) -> ProjectTarget:
        self.libraries[name] = self._target(linker.to_lib(name), sources, flags + BuildFlags().shared(), libs, compiler, include_dirs, linker, lib_dirs)
        return self.libraries[name]

    # Returns a profile if it exists, otherwise creates a new one and returns it.
    def profile(self, name, flags: BuildFlags=BuildFlags(), build_subdir: str=None) -> Profile:
        if name not in self.profiles:
            build_subdir = build_subdir or name
            build_dir = os.path.join(self.files.build_dir, build_subdir)
            self.profiles[name] = Profile(flags=flags, build_dir=build_dir)
        return self.profiles[name]

    # Prepares the project for a build.
    def configure(self) -> None:
        # Scan for all headers, and create the appropriate nodes.
        self.files.scan_all()
        self.configured = True
