from sbuildr.graph.node import Node, CompiledNode, LinkedNode
from sbuildr.project.file_manager import FileManager
from sbuildr.project.profile import Profile
from sbuildr.tools import compiler, linker
from sbuildr.tools.flags import BuildFlags
from sbuildr.project.target import ProjectTarget
from sbuildr.graph.graph import Graph
from sbuildr.logger import G_LOGGER

from typing import List, Set, Union, Dict, Tuple
from collections import OrderedDict, defaultdict
import inspect
import os

# TODO: Create a package manager to install dependencies.
class Project(object):
    """
    Represents a project. Projects include two default profiles with the following configuration:
    ``release``: ``BuildFlags().O(3).std(17).march("native").fpic()``
    ``debug``: ``BuildFlags().O(0).std(17).debug().fpic().define("S_DEBUG")``, attaches file suffix "_debug"
    These can be overridden using the ``profile()`` function.

    :param root: The path to the root directory for this project. All directories and files within the root directory are considered during searches for files. If no root directory is provided, defaults to the containing directory of the script calling this constructor.
    :param dirs: Additional directories outside the root directory that are part of the project. These directories and all contents will be considered during searches for files.
    :param build_dir: The build directory to use. If no build directory is provided, a directory named 'build' is created in the root directory.
    """
    def __init__(self, root: str=None, dirs: Set[str]=set(), build_dir: str=None, version: str=None):
        # The assumption is that the caller of the init function is the SBuildr file for the build.
        self.config_file = os.path.abspath(inspect.stack()[1][0].f_code.co_filename)
        root_dir = root if root else os.path.abspath(os.path.dirname(self.config_file))
        # Keep track of all files present in project dirs. Since dirs is a set, files is guaranteed
        # to contain no duplicates as well.
        # TODO: This will change once FileManager takes writable_dirs.
        self.files = FileManager(root_dir, build_dir, dirs)
        self.build_dir = self.files.build_dir
        # Set version to empty string if not provided. This is used for library suffixes.
        self.version = "" if version is None else version
        # Profiles consist of a graph of compiled/linked nodes. Each linked node is a
        # user-defined target for that profile.
        self.profiles: Dict[str, Profile] = {}
        # ProjectTargets combine linked nodes from one or more profiles for each user-defined target.
        # Each ProjectTarget maps profile names to their corresponding linked node for that target.
        self.executables: Dict[str, ProjectTarget] = {}
        self.tests: Dict[str, ProjectTarget] = {}
        self.libraries: Dict[str, ProjectTarget] = {}
        # Files installed by this project. Maps Nodes to installation paths.
        self.installs: Dict[Node, str] = {}
        # For targets, map profiles to nodes to be installed as well.
        self.profile_installs: Dict[str, List[Node]] = defaultdict(list)
        self.external_installs: Dict[Node, str] = {}
        # Add default profiles
        self.profile(name="release", flags=BuildFlags().O(3).std(17).march("native").fpic())
        self.profile(name="debug", flags=BuildFlags().O(0).std(17).debug().fpic().define("S_DEBUG"), file_suffix="_debug")

    def __contains__(self, target_name: str) -> bool:
        return target_name in self.executables or target_name in self.libraries

    # Prepares the project for a build.
    def prepare_for_build(self) -> None:
        # Scan for all headers, and create the appropriate nodes.
        self.files.scan_all()

    def _target(self,
                name: str,
                basename: str,
                sources: List[str],
                flags: BuildFlags,
                libs: List[Union[ProjectTarget,
                str]],
                compiler: compiler.Compiler,
                include_dirs: List[str],
                linker: linker.Linker,
                lib_dirs: List[str]) -> ProjectTarget:
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
        """
        Adds an executable target to all profiles within this project.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either 'ProjectTarget's or strings (which may be either library names or paths to libraries) against which to link. Paths must be absolute paths, so as to disambiguate from library names.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param lib_dirs: A list of paths for directories containing libraries needed by this target.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
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
        """
        Adds an executable target to all profiles within this project. Test targets can be automatically built and run by using the ``test`` command on the CLI.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either 'ProjectTarget's or strings (which may be either library names or paths to libraries) against which to link. Paths must be absolute paths, so as to disambiguate from library names.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param lib_dirs: A list of paths for directories containing libraries needed by this target.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
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
        """
        Adds a library target to all profiles within this project.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either 'ProjectTarget's or strings (which may be either library names or paths to libraries) against which to link. Paths must be absolute paths, so as to disambiguate from library names.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param lib_dirs: A list of paths for directories containing libraries needed by this target.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.libraries[name] = self._target(name, linker.to_lib(name), sources, flags + BuildFlags()._enable_shared(), libs, compiler, include_dirs, linker, lib_dirs)
        self.libraries[name].is_lib = True
        return self.libraries[name]

    # Returns a profile if it exists, otherwise creates a new one and returns it.
    # TODO: build_subdir should be able to handle absolute paths too. The profile build directory can be outside the main build directory. However, the file manager's writable directories would need to updated.
    def profile(self, name: str, flags: BuildFlags=BuildFlags(), build_subdir: str=None, file_suffix: str="") -> Profile:
        """
        Returns or creates a profile with the specified parameters.

        :param name: The name of this profile.
        :param flags: The flags to use for this profile. These will be applied to all targets for this profile. Per-target flags always take precedence.
        :param build_subdir: The name of the build subdirectory to use. This should NOT be a path, as it will always be created as a subdirectory of the project's build directory.
        :param file_suffix: A file suffix to attach to all artifacts generated for this profile. For example, the default debug profile attaches a ``_debug`` suffix to all library and executable names.

        :returns: :class:`sbuildr.Profile`
        """
        if name not in self.profiles:
            build_subdir = build_subdir or name
            if os.path.isabs(build_subdir):
                G_LOGGER.critical(f"Build subdirectory for profile {name} should not be a path, but was set to {build_subdir}")
            build_dir = os.path.join(self.files.build_dir, build_subdir)
            self.profiles[name] = Profile(flags=flags, build_dir=build_dir, suffix=file_suffix)
        return self.profiles[name]

    def install(self, target: Union[ProjectTarget, str], path: str, profile: str="release") -> str:
        """
        Specifies that a project target or file should be installed to the provided path or directory.
        When running the ``install`` command on the CLI, the targets and files specified via this function will be copied to their respective destination directories.

        :param target: A project target or path to a file to install.
        :param path: The desired installation path. May be a directory or path.
        :param profile: The profile whose target to install. Defaults to "release". This is unused if ``target`` is a file path.

        :returns: The path to which the target or file will be installed.
        """
        path = self.files.abspath(path)

        def generate_install_path(filename: str):
            if os.path.isdir(path):
                return os.path.join(path, filename)
            return path

        if isinstance(target, ProjectTarget):
            if profile not in target:
                G_LOGGER.critical(f"Could not find profile: {profile} in target: {target}. Available profiles for this target are: {list(target.keys())}")
            node = target[profile]
            self.profile_installs[profile].append(node)
            install_path = generate_install_path(node.name)
            self.installs[node] = install_path
            G_LOGGER.verbose(f"Set install path for {node.name} ({node.path}) to {self.installs[node]}")
        else:
            candidates = self.files.find(target)
            if len(candidates) == 0:
                G_LOGGER.critical(f"Could not find installation target: {target}")
            if len(candidates) > 1:
                G_LOGGER.critical(f"For installation target: {target}, found multiple installation candidates: {candidates}. Please provide a longer path to disambiguate.")
            node = self.files.external(candidates[0])
            # For files, node.name is guaranteed to be the file basename
            install_path = generate_install_path(node.name)
            self.external_installs[node] = install_path
            G_LOGGER.verbose(f"Set install path for {node.name} ({node.path}) to {self.external_installs[node]}")
        return install_path
