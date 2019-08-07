from sbuildr.graph.node import Node, CompiledNode, LinkedNode
from sbuildr.project.file_manager import FileManager
from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.backends.backend import Backend
from sbuildr.project.target import ProjectTarget
from sbuildr.logger import G_LOGGER, plural
from sbuildr.project.profile import Profile
from sbuildr.tools import compiler, linker
from sbuildr.tools.flags import BuildFlags
from sbuildr.graph.graph import Graph
from sbuildr.misc import paths, utils
from sbuildr import logger

from typing import List, Set, Union, Dict, Tuple
from collections import OrderedDict, defaultdict
import subprocess
import inspect
import pickle
import sys
import os

class Project(object):
    """
    Represents a project. Projects include two default profiles with the following configuration:
    ``release``: ``BuildFlags().O(3).std(17).march("native").fpic()``
    ``debug``: ``BuildFlags().O(0).std(17).debug().fpic().define("S_DEBUG")``, attaches file suffix "_debug"
    These can be overridden using the ``profile()`` function.

    :param root: The path to the root directory for this project. All directories and files within the root directory are considered during searches for files. If no root directory is provided, defaults to the containing directory of the script calling this constructor.
    :param dirs: Additional directories outside the root directory that are part of the project. These directories and all contents will be considered during searches for files.
    :param build_dir: The build directory to use. If no build directory is provided, a directory named 'build' is created in the root directory.
    :param BackendType: The type of backend to use. Since SBuildr is a meta-build system, it can support multiple backends to perform builds. For example, RBuild (i.e. ``sbuildr.backends.RBuildBackend``) can be used for fast incremental builds. Note that this should be a type rather than an instance of a backend.
    """
    def __init__(self, root: str=None, dirs: Set[str]=set(), build_dir: str=None, BackendType: type=RBuildBackend):
        # The assumption is that the caller of the init function is the SBuildr file for the build.
        self.config_file = os.path.abspath(inspect.stack()[1][0].f_code.co_filename)
        root_dir = root if root else os.path.abspath(os.path.dirname(self.config_file))
        # Keep track of all files present in project dirs. Since dirs is a set, files is guaranteed
        # to contain no duplicates as well.
        # TODO: This will change once FileManager takes writable_dirs.
        self.files = FileManager(root_dir, build_dir, dirs)
        self.build_dir = self.files.build_dir
        # Backend
        self.backend = BackendType(self.build_dir)
        # Profiles consist of a graph of compiled/linked nodes. Each linked node is a
        # user-defined target for that profile.
        self.profiles: Dict[str, Profile] = {}
        # ProjectTargets combine linked nodes from one or more profiles for each user-defined target.
        # Each ProjectTarget maps profile names to their corresponding linked node for that target.
        self.executables: Dict[str, ProjectTarget] = {}
        self.tests: Dict[str, ProjectTarget] = {}
        self.libraries: Dict[str, ProjectTarget] = {}
        # Files installed by this project. Maps Nodes to installation paths.
        self.public_headers: Set[str] = {}
        # Add default profiles
        self.profile(name="release", flags=BuildFlags().O(3).std(17).march("native").fpic())
        self.profile(name="debug", flags=BuildFlags().O(0).std(17).debug().fpic().define("S_DEBUG"), file_suffix="_debug")

    @staticmethod
    def load(path: str=None) -> "Project":
        """
        Load a project from the specified path.

        :param path: The path from which to load the project. Defaults to ``os.path.join("build", "project.sbuildr")``

        :returns: The loaded project.
        """
        path = path or os.path.join("build", "project.sbuildr")
        with open(path, "rb") as f:
            return pickle.load(f)

    def __contains__(self, target_name: str) -> bool:
        return target_name in self.executables or target_name in self.libraries

    def _target(self,
                name: str,
                basename: str,
                sources: List[str],
                flags: BuildFlags,
                libs: List[Union[ProjectTarget, str]],
                compiler: compiler.Compiler,
                include_dirs: List[str],
                linker: linker.Linker,
                lib_dirs: List[str],
                internal: bool) -> ProjectTarget:
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

        # TODO: Add Loader class so that we know how to run things that depend on these libraries.
        # TODO: If the LinkedNode has any inputs that are not CompiledNodes, then they are libraries, and must be added to the loader path.
        source_nodes = get_source_nodes(sources)
        libs: List[Union[ProjectTarget, Node, str]] = get_libraries(libs)
        target = ProjectTarget(name=name, internal=internal)
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
                    lib_dirs: List[str] = [],
                    internal = False) -> ProjectTarget:
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
        :param internal: Whether this target is internal to the project, in which case it will not be installed.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.executables[name] = self._target(name, paths.execname(name), sources, flags, libs, compiler, include_dirs, linker, lib_dirs, internal)
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
        self.tests[name] = self._target(name, paths.execname(name), sources, flags, libs, compiler, include_dirs, linker, lib_dirs, True)
        return self.tests[name]

    def library(self,
                name: str,
                sources: List[str],
                flags: BuildFlags = BuildFlags(),
                libs: List[Union[ProjectTarget, str]] = [],
                compiler: compiler.Compiler = compiler.clang,
                include_dirs: List[str] = [],
                linker: linker.Linker = linker.clang,
                lib_dirs: List[str] = [],
                internal = False) -> ProjectTarget:
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
        :param internal: Whether this target is internal to the project, in which case it will not be installed.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.libraries[name] = self._target(name, paths.libname(name), sources, flags + BuildFlags()._enable_shared(), libs, compiler, include_dirs, linker, lib_dirs, internal)
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

    def interfaces(self, headers: List[str]) -> List[str]:
        """
        Specifies headers that are part of this project's public interface.
        When running the ``install`` command on the CLI, the headers specified via this function will be copied to installation directories.

        :param headers: A list of paths to a public headers.

        :returns: The absolute paths of the discovered headers.
        """
        discovered_paths = []
        for header in headers:
            candidates = self.files.find(header)
            if len(candidates) == 0:
                G_LOGGER.critical(f"Could not find installation target: {target}")
            if len(candidates) > 1:
                G_LOGGER.critical(f"For installation target: {target}, found multiple installation candidates: {candidates}. Please provide a longer path to disambiguate.")
            discovered_paths.append(candidates[0])
        self.public_headers = set(discovered_paths)
        return discovered_paths


    def find(self, path) -> str:
        """
        Attemps to locate a path in the project. If no paths were found, or multiple ambiguous paths were found, raises an exception.

        :param path: The path to find. This may be an absolute path, partial path, or file/directory name.

        :returns: An absolute path to the matching file or directory.
        """
        candidates = self.files.find(path)
        if len(candidates) == 0:
            G_LOGGER.critical(f"Could not find path: {path}")
        elif len(candidates) > 1:
            G_LOGGER.critical(f"For path: {path}, found multiple candidates: {candidates}. Please provide a longer path to disambiguate.")
        return candidates[0]


    def freeze(self, path: str=None) -> None:
        """
        Freeze this project for build and save to the specified path. This includes generating any build configuration files required by this project's backend. This way, it is possible to build without having to run the build script each time.
        New targets should not be added to a frozen project.

        :param path: The path at which to save the project. Defaults to ``os.path.join(self.build_dir, "project.sbuildr")``
        """
        self.files.mkdir(self.build_dir)
        self.backend.configure(self.files.graph, [profile.graph for profile in self.profiles.values()])
        path = path or os.path.join(self.build_dir, "project.sbuildr")
        with open(path, "wb") as f:
            pickle.dump(self, f)


    def build(self, targets: List[ProjectTarget], profile_names: List[str]=[]) -> float:
        """
        Builds the specified targets for this project. Configuration should be run prior to calling this function.

        :param targets: The targets to build.
        :param profile_names: The profiles for which to build the targets. If no profiles are specified, the project builds for all profiles.

        :returns: Time elapsed during the build.
        """
        G_LOGGER.info(f"Building targets: {[target.name for target in targets]} for profiles: {profile_names}")
        G_LOGGER.debug(f"Targets: {targets}")

        def select_nodes(targets: List[ProjectTarget], profile_names: List[str]) -> List[Node]:
            # Create all required profile build directories and populate nodes.
            nodes = []
            for prof_name in profile_names:
                if prof_name not in self.profiles:
                    G_LOGGER.critical(f"Profile {prof_name} does not exist in the project. Available profiles: {list(project.profiles.keys())}")
                self.files.mkdir(self.profiles[prof_name].build_dir)
                # Populate nodes.
                for target in targets:
                    if prof_name in target:
                        node = target[prof_name]
                        G_LOGGER.verbose(f"For target: {target}, profile: {prof_name}, found path: {node.path}")
                        nodes.append(node)
                    else:
                        G_LOGGER.debug(f"Skipping target: {target.name} for profile: {prof_name}, as it does not exist.")
            return nodes

        profile_names = profile_names or self.profiles.keys()
        nodes = select_nodes(targets, profile_names)
        status, time_elapsed = self.backend.build(nodes)
        if status.returncode:
            G_LOGGER.critical(f"Failed with:\n{utils.subprocess_output(status)}\nReconfiguring the project or running a clean build may resolve this.")
        G_LOGGER.info(f"Built {plural('target', len(targets))} for {plural('profile', len(profile_names))} in {time_elapsed} seconds.")
        return time_elapsed


    # TODO(0): Docstring
    # TODO: Set up LD_LIBRARY_PATH correctly here
    def run(self, targets: List[ProjectTarget], profile_names: List[str]=[]):
        """
        Runs targets from this project.
        """
        for target in targets:
            if target.name not in self.executables:
                G_LOGGER.critical(f"Could not find target: {target.name} in project executables. Note: Available executables are: {list(self.executables.keys())}")

        def run_target(target: ProjectTarget, prof_name: str):
            G_LOGGER.log(f"\nRunning target: {target}, for profile: {prof_name}: {target[prof_name].path}", color=logger.Color.GREEN)
            status = subprocess.run([target[prof_name].path], capture_output=True)
            output = utils.subprocess_output(status)
            G_LOGGER.log(output)
            if result.returncode:
                G_LOGGER.critical(f"Failed to run. Reconfiguring the project or running a clean build may resolve this.")

        self.build(targets, profile_names)
        for prof_name in profile_names:
            G_LOGGER.log(f"\n{utils.wrap_str(f' Profile: {prof_name} ')}", color=logger.Color.GREEN)
            for target in targets:
                run_target(target, prof_name)

    # TODO(0): Docstring
    # TODO: Set up LD_LIBRARY_PATH correctly here
    def run_tests(self, targets: List[ProjectTarget]=[], profile_names: List[str]=[]):
        """
        Run tests from this project. Runs all tests from the project for all profiles by default.
        """
        for target in targets:
            if target.name not in self.tests:
                G_LOGGER.critical(f"Could not find test: {target.name} in project.\n\tAvailable tests:\n\t\t{list(self.tests.keys())}")

        tests = targets or list(self.tests.values())
        profile_names = profile_names or list(self.profiles.keys())
        if not tests:
            G_LOGGER.warning(f"No tests found. Have you registered tests using project.test()?")
            return

        # Otherwise, build and run the specified tests
        self.build(tests, profile_names)

        class TestResult:
            def __init__(self):
                self.failed = 0
                self.passed = 0

        def run_test(test, prof_name):
            G_LOGGER.log(f"\nRunning test: {test}, for profile: {prof_name}: {test[prof_name].path}\n", color=logger.Color.GREEN)
            status = subprocess.run([test[prof_name].path])
            if status.returncode:
                G_LOGGER.log(f"\nFAILED {test}, for profile: {prof_name}:\n{test[prof_name].path}", color=logger.Color.RED)
                test_results[prof_name].failed += 1
                failed_targets[prof_name].add(test[prof_name].name)
            else:
                G_LOGGER.log(f"\nPASSED {test}", color=logger.Color.GREEN)
                test_results[prof_name].passed += 1

        test_results = defaultdict(TestResult)
        failed_targets = defaultdict(set)
        for prof_name in profile_names:
            G_LOGGER.log(f"\n{utils.wrap_str(f' Profile: {prof_name} ')}", color=logger.Color.GREEN)
            for test in tests:
                run_test(test, prof_name)

        # Display summary
        G_LOGGER.log(f"\n{utils.wrap_str(f' Test Results Summary ')}\n", color=logger.Color.GREEN)
        for prof_name, result in test_results.items():
            if result.passed or result.failed:
                G_LOGGER.log(f"Profile: {prof_name}", color=logger.Color.GREEN)
                if result.passed:
                    G_LOGGER.log(f"\tPASSED {plural('test', result.passed)}", color=logger.Color.GREEN)
                if result.failed:
                    G_LOGGER.log(f"\tFAILED {plural('test', result.failed)}: {failed_targets[prof_name]}", color=logger.Color.RED)


    def _all_targets(self):
        return list(self.libraries.values()) + list(self.executables.values())

    def install(self,
        targets: List[ProjectTarget]=[],
        profile_names: List[str]=[],
        headers: List[str]=[],
        header_install_path: str=paths.default_header_install_path(),
        library_install_path: str=paths.default_library_install_path(),
        executable_install_path: str=paths.default_executable_install_path(),
        dry_run: bool=True):
        """
        Install the specified targets for the specified profiles.

        :param targets: The targets to install. Defaults to all non-internal project targets.
        :param profile_names: The profiles for which to install. Defaults to the "release" profile.
        :param headers: The headers to install. Defaults to all headers that are part of the interface as per :func:`interfaces` .
        :param header_install_path: The path to which to install headers. This defaults to one of the default locations for the host OS.
        :param library_install_path: The path to which to install libraries. This defaults to one of the default locations for the host OS.
        :param executable_install_path: The path to which to install executables. This defaults to one of the default locations for the host OS.
        :param dry_run: Whether to perform a dry-run only, with no file copying. Defaults to True.
        """
        targets = targets or [target for target in self._all_targets() if not target.internal]
        profile_names = profile_names or ["release"]
        headers = [self.find(header) for header in headers] or list(self.public_headers)

        if dry_run:
            G_LOGGER.warning(f"Install dry-run, will not copy files.")

        def install_target(target, prof_name):
            node = target[prof_name]
            install_dir = library_install_path if target.is_lib else executable_install_path
            install_path = os.path.join(install_dir, node.name)
            if dry_run:
                G_LOGGER.info(f"Would install target: {node.name} to {install_path}")
            else:
                if utils.copy_path(node.path, install_path):
                    G_LOGGER.info(f"Installed target: {node.name} to {install_path}")

        for prof_name in profile_names:
            for target in targets:
                install_target(target, prof_name)

        def install_header(header):
            install_path = os.path.join(header_install_path, os.path.basename(header))
            if dry_run:
                G_LOGGER.info(f"Would install header: {header} to {install_path}")
            else:
                if utils.copy_path(header, install_path):
                    G_LOGGER.info(f"Installed header: {header} to {install_path}")

        for header in headers:
            install_header(header)


    def uninstall(self,
        targets: List[ProjectTarget]=[],
        profile_names: List[str]=[],
        headers: List[str]=[],
        header_install_path: str=paths.default_header_install_path(),
        library_install_path: str=paths.default_library_install_path(),
        executable_install_path: str=paths.default_executable_install_path(),
        dry_run: bool=True):
        """
        Uninstall the specified targets for the specified profiles.

        :param targets: The targets to uninstall. Defaults to all non-internal project targets.
        :param profile_names: The profiles for which to uninstall. Defaults to the "release" profile.
        :param headers: The headers to uninstall. Defaults to all headers that are part of the interface as per :func:`interfaces` .
        :param header_install_path: The path from which to uninstall headers. This defaults to one of the default locations for the host OS.
        :param library_install_path: The path from which to uninstall libraries. This defaults to one of the default locations for the host OS.
        :param executable_install_path: The path from which to uninstall executables. This defaults to one of the default locations for the host OS.
        :param dry_run: Whether to perform a dry-run only, with no file copying. Defaults to True.
        """
        targets = targets or [target for target in self._all_targets() if not target.internal]
        profile_names = profile_names or ["release"]
        headers = [self.find(header) for header in headers] or list(self.public_headers)

        if dry_run:
            G_LOGGER.warning(f"Uninstall dry-run, will not remove files.")

        def uninstall_target(target, prof_name):
            node = target[prof_name]
            uninstall_dir = library_install_path if target.is_lib else executable_install_path
            uninstall_path = os.path.join(uninstall_dir, node.name)
            if dry_run:
                G_LOGGER.info(f"Would remove target: {node.name} from {uninstall_path}")
            else:
                os.remove(uninstall_path)
                G_LOGGER.info(f"Uninstalled target: {node.name} from {uninstall_path}")

        for prof_name in profile_names:
            for target in targets:
                uninstall_target(target, prof_name)

        def uninstall_header(header):
            uninstall_path = os.path.join(header_install_path, os.path.basename(header))
            if dry_run:
                G_LOGGER.info(f"Would remove header: {header} from {uninstall_path}")
            else:
                os.remove(uninstall_path)
                G_LOGGER.info(f"Uninstalled header: {header} from {uninstall_path}")

        for header in headers:
            uninstall_header(header)


    # TODO(0): Docstring
    def clean(self, profile_names: List[str]=[], nuke: bool=False, dry_run: bool=True):
        """
        Removes build directories and project artifacts.
        """
        # TODO(3): Add per-target cleaning.
        to_remove = []
        if dry_run:
            G_LOGGER.warning(f"Clean dry-run, will not remove files.")

        if nuke:
            # The nuclear option
            to_remove = [self.build_dir]
            G_LOGGER.info(f"Initiating Nuclear Protocol!")
        else:
            # By default, cleans all targets for all profiles.
            profile_names = profile_names or list(self.profiles.keys())
            to_remove = [self.profiles[prof_name].build_dir for prof_name in profile_names]
            G_LOGGER.info(f"Cleaning targets for profiles: {prof_names}")
        # Remove
        for path in to_remove:
            if dry_run:
                G_LOGGER.info(f"Would remove: {path}")
            else:
                project.files.rm(path)
