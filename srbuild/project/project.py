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
        self.config_file = os.path.abspath(inspect.stack()[1][0].f_code.co_filename)
        root_dir = root if root else os.path.abspath(os.path.dirname(self.config_file))
        # Keep track of all files present in project dirs. Since dirs is a set, files is guaranteed
        # to contain no duplicates as well.
        # TODO: This will change once FileManager takes writable_dirs.
        self.files = FileManager(root_dir, build_dir, dirs)
        self.build_dir = self.files.build_dir
        # Profiles consist of a graph of compiled/linked nodes. Each linked node is a
        # user-defined target for that profile.
        self.profiles: Dict[str, Profile] = {}
        # ProjectTargets combine linked nodes from one or more profiles for each user-defined target.
        # Each ProjectTarget maps profile names to their corresponding linked node for that target.
        self.executables: Dict[str, ProjectTarget] = {}
        self.tests: Dict[str, ProjectTarget] = {}
        self.libraries: Dict[str, ProjectTarget] = {}
        # Extra files installed by this project.
        self.installs: Dict[str, str] = {}
        # Add default profiles
        self.profile(name="release", flags=BuildFlags().O(3).std(17).march("native").fpic())
        self.profile(name="debug", flags=BuildFlags().O(0).std(17).debug().fpic(), file_suffix="_debug")

    def __contains__(self, target_name: str) -> bool:
        return target_name in self.executables or target_name in self.libraries

    # Prepares the project for a build.
    def prepare_for_build(self) -> None:
        # Scan for all headers, and create the appropriate nodes.
        self.files.scan_all()

    def _target(self, name: str, basename: str, sources: List[str], flags: BuildFlags, libs: List[Union[ProjectTarget, str]], compiler: compiler.Compiler, include_dirs: List[str], linker: linker.Linker, lib_dirs: List[str]) -> ProjectTarget:
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
                # Targets are handled for each profile individually
                if not isinstance(lib, ProjectTarget):
                    candidates = self.files.find(lib)
                    if is_lib_path(lib):
                        if len(candidates) > 1:
                            G_LOGGER.warning(f"For library: {lib}, found multiple candidates: {candidates}. Using {candidates[0]}. If this is incorrect, please provide a longer path to disambiguate.")
                        # Add the library to the file manager as an external path
                        lib = self.files.external(lib)
                    elif candidates:
                        G_LOGGER.warning(f"For library: {lib}, found matching paths: {candidates}. However, {lib} appears to be a library name rather than a path to a library. If you meant to use a path, please provide a longer path to disambiguate.")
                fixed_libs.append(lib)
            G_LOGGER.debug(f"Using fixed libs: {fixed_libs}")
            return fixed_libs

        source_nodes = get_source_nodes(sources)
        libs: List[Union[ProjectTarget, Node, str]] = get_libraries(libs)
        target = ProjectTarget(name=name)
        for profile_name, profile in self.profiles.items():
            # Process targets so we only give each profile its own LinkedNodes.
            # Purposely don't convert all libs to paths here, so that each profile can set up dependencies correctly.
            target_libs = [lib if not isinstance(lib, ProjectTarget) else lib[profile_name] for lib in libs]
            G_LOGGER.debug(f"Adding target: {name}, with basename: {basename} to profile: {profile_name}")
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
        self.executables[name] = self._target(name, linker.to_exec(name), sources, flags, libs, compiler, include_dirs, linker, lib_dirs)
        return self.executables[name]

    def test(self,
                name: str,
                sources: List[str],
                flags: BuildFlags = BuildFlags(),
                libs: List[Union[ProjectTarget, str]] = [],
                compiler: compiler.Compiler = compiler.clang,
                include_dirs: List[str] = [],
                linker: linker.Linker = linker.clang,
                lib_dirs: List[str] = []) -> ProjectTarget:
        self.tests[name] = self._target(name, linker.to_exec(name), sources, flags, libs, compiler, include_dirs, linker, lib_dirs)
        return self.tests[name]

    def library(self,
                name: str,
                sources: List[str],
                flags: BuildFlags = BuildFlags(),
                libs: List[Union[ProjectTarget, str]] = [],
                compiler: compiler.Compiler = compiler.clang,
                include_dirs: List[str] = [],
                linker: linker.Linker = linker.clang,
                lib_dirs: List[str] = []) -> ProjectTarget:
        self.libraries[name] = self._target(name, linker.to_lib(name), sources, flags + BuildFlags().shared(), libs, compiler, include_dirs, linker, lib_dirs)
        self.libraries[name].is_lib = True
        return self.libraries[name]

    # Returns a profile if it exists, otherwise creates a new one and returns it.
    def profile(self, name, flags: BuildFlags=BuildFlags(), build_subdir: str=None, file_suffix="") -> Profile:
        if name not in self.profiles:
            build_subdir = build_subdir or name
            if os.path.isabs(build_subdir):
                G_LOGGER.critical(f"Build subdirectory for profile {name} should not be a path, but was set to {build_subdir}")
            build_dir = os.path.join(self.files.build_dir, build_subdir)
            self.profiles[name] = Profile(flags=flags, build_dir=build_dir, suffix=file_suffix)
        return self.profiles[name]

    # TODO: Docstrings
    # FIXME: This should be able to install to a file now.
    def install(self, target: Union[ProjectTarget, str], dir: str):
        if os.path.isfile(dir):
            G_LOGGER.critical(f"Cannot currently install to a file. Please specify a directory instead.")
        dir_path = self.files.abspath(dir)
        if isinstance(target, ProjectTarget):
            for profile, node in target.items():
                node.install_path = os.path.join(dir_path, node.name)
                G_LOGGER.verbose(f"Set install path for {node.name} ({node.path}) to {node.install_path}")
        else:
            candidates = self.files.find(target)
            if len(candidates) == 0:
                G_LOGGER.critical(f"Could not find installation target: {target}")
            if len(candidates) > 1:
                G_LOGGER.critical(f"For installation target: {target}, found multiple installation candidates: {candidates}. Please provide a longer path to disambiguate.")
            path = candidates[0]
            self.installs[path] = os.path.join(dir_path, os.path.basename(path))
