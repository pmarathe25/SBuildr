from sbuildr.graph.node import Node, CompiledNode, LinkedNode, Library
from sbuildr.dependencies.dependency import DependencyLibrary
from sbuildr.project.file_manager import FileManager
from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.project.target import ProjectTarget
from sbuildr.backends.backend import Backend
from sbuildr.logger import G_LOGGER, plural
from sbuildr.project.profile import Profile
from sbuildr.tools import compiler, linker
from sbuildr.tools.flags import BuildFlags
from sbuildr.graph.graph import Graph
from sbuildr.misc import paths, utils
from sbuildr import logger
import sbuildr

from typing import List, Set, Union, Dict, Tuple
from collections import OrderedDict, defaultdict
import subprocess
import inspect
import pickle
import sys
import os

class Project(object):
    DEFAULT_SAVED_PROJECT_NAME = "project.sbuildr"
    """
    Represents a project. Projects include two default profiles with the following configuration:
    ``release``: ``BuildFlags().O(3).std(17).march("native").fpic()``
    ``debug``: ``BuildFlags().O(0).std(17).debug().fpic().define("S_DEBUG")``, attaches file suffix "_debug"
    These can be overridden using the ``profile()`` function.

    :param root: The path to the root directory for this project. All directories and files within the root directory are considered during searches for files. If no root directory is provided, defaults to the containing directory of the script calling this constructor.
    :param dirs: Additional directories outside the root directory that are part of the project. These directories and all contents will be considered during searches for files.
    :param build_dir: The build directory to use. If no build directory is provided, a directory named 'build' is created in the root directory.
    """
    def __init__(self, root: str=None, dirs: Set[str]=set(), build_dir: str=None):
        self.sbuildr_version = sbuildr.__version__
        # The assumption is that the caller of the init function is the SBuildr file for the build.
        self.config_file = os.path.abspath(inspect.stack()[1][0].f_code.co_filename)
        # Keep track of all files present in project dirs. Since dirs is a set, files is guaranteed
        # to contain no duplicates as well.
        self.files = FileManager(root or os.path.abspath(os.path.dirname(self.config_file)), dirs)
        # The build directory will be writable, and excluded when the FileManager is searching for paths.
        self.build_dir = self.files.add_writable_dir(self.files.add_exclude_dir(build_dir or os.path.join(self.files.root_dir, "build")))
        # TODO: Make this a parameter?
        self.common_objs_build_dir = os.path.join(self.build_dir, "common")
        # Backend
        self.backend = None
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
        # A graph describing the entire project. This is typically not constructed until just before the build
        self.graph: Graph = None


    @staticmethod
    def load(path: str=None) -> "Project":
        f"""
        Load a project from the specified path.

        :param path: The path from which to load the project. Defaults to {os.path.abspath(Project.DEFAULT_SAVED_PROJECT_NAME)}

        :returns: The loaded project.
        """
        path = path or os.path.abspath(Project.DEFAULT_SAVED_PROJECT_NAME)
        with open(path, "rb") as f:
            return pickle.load(f)


    def export(self, path: str=None) -> None:
        f"""
        Export this project to the specified path. When invoked within an SBuildr configuration script, this enables the project to be used with SBuildr's dependency management system.

        :param path: The path at which to export the project. Defaults to {Project.DEFAULT_SAVED_PROJECT_NAME} in the project's root directory.
        """
        path = path or os.path.join(self.files.root_dir, Project.DEFAULT_SAVED_PROJECT_NAME)
        with open(path, "wb") as f:
            pickle.dump(self, f)


    def __contains__(self, target_name: str) -> bool:
        return target_name in self.executables or target_name in self.libraries


    def all_targets(self):
        return list(self.libraries.values()) + list(self.executables.values()) + list(self.tests.values())


    def all_profile_names(self) -> List[str]:
        return list(self.profiles.keys())


    def _target(self,
                name: str,
                basename: str,
                sources: List[str],
                flags: BuildFlags,
                libs: List[Union[DependencyLibrary, ProjectTarget, Library]],
                compiler: compiler.Compiler,
                include_dirs: List[str],
                linker: linker.Linker,
                internal: bool) -> ProjectTarget:
        if not all([isinstance(lib, ProjectTarget) or isinstance(lib, Library) or isinstance(lib, DependencyLibrary) for lib in libs]):
            G_LOGGER.critical(f"Libraries must be instances of either sbuildr.Library, sbuildr.dependencies.DependencyLibrary or sbuildr.ProjectTarget")

        # Convert sources to full paths
        def get_source_nodes(sources: List[str]) -> List[CompiledNode]:
            source_nodes: List[CompiledNode] = [self.files.source(path) for path in sources]
            G_LOGGER.verbose(f"For sources: {sources}, found source paths: {source_nodes}")
            return source_nodes

        # Inserts suffix into path, just before the extension
        def file_suffix(path: str, suffix: str, ext: str = None) -> str:
            split = os.path.splitext(os.path.basename(path))
            suffixed = f"{split[0]}{suffix}{(ext or split[1] or '')}"
            G_LOGGER.verbose(f"Received path: {path}, split into {split}. Using suffix: {suffix}, generated final name: {suffixed}")
            return suffixed

        # For any DependencyLibrarys in libs, add them to the target's dependencies, and then extract the Library.
        dependent_libraries: List[DependencyLibrary] = [lib for lib in libs if isinstance(lib, DependencyLibrary)]
        # Inherit dependent_libraries from any input libraries as well
        [dependent_libraries.extend(lib.dependent_libraries) for lib in libs if isinstance(lib, ProjectTarget)]
        libs: List[Union[ProjectTarget, Library]] = [lib.library if isinstance(lib, DependencyLibrary) else lib for lib in libs]

        source_nodes = get_source_nodes(sources)
        target = ProjectTarget(name=name, internal=internal, dependent_libraries=dependent_libraries)
        for profile_name, profile in self.profiles.items():
            # Convert all libraries to nodes. These will be inputs to the target.
            # Profile will later convert them to library names and directories.
            input_nodes = [lib[profile_name] if isinstance(lib, ProjectTarget) else lib for lib in libs]
            G_LOGGER.verbose(f"Library inputs for target: {name} are: {input_nodes}")

            # Per-target flags always overwrite profile flags.
            flags = profile.flags + flags

            # First, add or retrieve object nodes for each source.
            for source_node in source_nodes:
                # Only the include dirs provided by the user are part of the hash. When the automatically deduced
                # include_dirs change, it means the file is stale, so name collisions don't matter (i.e. OK to overwrite.)
                obj_sig = compiler.signature(source_node.path, include_dirs, flags)
                obj_path = os.path.join(self.common_objs_build_dir, file_suffix(source_node.path, f".{obj_sig}", ".o"))
                # User defined includes are always prepended the ones deduced for SourceNodes.
                obj_node = CompiledNode(obj_path, source_node, compiler, include_dirs, flags)
                input_nodes.append(profile.graph.add(obj_node))

            # TODO: Add back linker signature, create hard links using always clause in rbuild.
            # Finally, add the actual linked node
            linked_path = os.path.join(profile.build_dir, file_suffix(basename, profile.suffix))
            linked_node = LinkedNode(linked_path, input_nodes, linker, flags=flags)
            G_LOGGER.debug(f"Adding target: {name}, with path: {linked_path} to profile: {profile_name}")
            target[profile_name] = profile.graph.add(linked_node)
        return target


    # Both of these functions will modify name before passing it to profile so that the filename is correct.
    def executable(self,
                    name: str,
                    sources: List[str],
                    flags: BuildFlags = BuildFlags(),
                    libs: List[Union[DependencyLibrary, ProjectTarget, Library]] = [],
                    compiler: compiler.Compiler = compiler.clang,
                    include_dirs: List[str] = [],
                    linker: linker.Linker = linker.clang,
                    internal = False) -> ProjectTarget:
        """
        Adds an executable target to all profiles within this project.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either ``ProjectTarget``s, ``DependencyLibrary``s or ``Library``s.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param internal: Whether this target is internal to the project, in which case it will not be installed.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.executables[name] = self._target(name, paths.name_to_execname(name), sources, flags, libs, compiler, include_dirs, linker, internal)
        return self.executables[name]


    def test(self,
                name: str,
                sources: List[str],
                flags: BuildFlags = BuildFlags(),
                libs: List[Union[DependencyLibrary, ProjectTarget, Library]] = [],
                compiler: compiler.Compiler = compiler.clang,
                include_dirs: List[str] = [],
                linker: linker.Linker = linker.clang) -> ProjectTarget:
        """
        Adds an executable target to all profiles within this project. Test targets can be automatically built and run by using the ``test`` command on the CLI.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either ``ProjectTarget``s, ``DependencyLibrary``s or ``Library``s.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.tests[name] = self._target(name, paths.name_to_execname(name), sources, flags, libs, compiler, include_dirs, linker, True)
        return self.tests[name]


    def library(self,
                name: str,
                sources: List[str],
                flags: BuildFlags = BuildFlags(),
                libs: List[Union[DependencyLibrary, ProjectTarget, Library]] = [],
                compiler: compiler.Compiler = compiler.clang,
                include_dirs: List[str] = [],
                linker: linker.Linker = linker.clang,
                internal = False) -> ProjectTarget:
        """
        Adds a library target to all profiles within this project.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either ``ProjectTarget``s, ``DependencyLibrary``s or ``Library``s.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param internal: Whether this target is internal to the project, in which case it will not be installed.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.libraries[name] = self._target(name, paths.name_to_libname(name), sources, flags + BuildFlags()._enable_shared(), libs, compiler, include_dirs, linker, internal)
        self.libraries[name].is_lib = True
        return self.libraries[name]


    # Returns a profile if it exists, otherwise creates a new one and returns it.
    def profile(self, name: str, flags: BuildFlags=BuildFlags(), build_dir: str=None, file_suffix: str="") -> Profile:
        """
        Returns or creates a profile with the specified parameters.

        :param name: The name of this profile.
        :param flags: The flags to use for this profile. These will be applied to all targets for this profile. Per-target flags always take precedence.
        :param build_dir: The name of the build subdirectory to use. This should NOT be a path, as it will always be created as a subdirectory of the project's build directory.
        :param file_suffix: A file suffix to attach to all artifacts generated for this profile. For example, the default debug profile attaches a ``_debug`` suffix to all library and executable names.

        :returns: :class:`sbuildr.Profile`
        """
        if name not in self.profiles:
            build_dir = self.files.add_writable_dir(self.files.add_exclude_dir(os.path.abspath(build_dir or os.path.join(self.build_dir, name))))
            G_LOGGER.verbose(f"Setting build directory for profile: {name} to: {build_dir}")
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


    # TODO(0): TEST THIS
    def fetch_dependencies(self, targets: List[ProjectTarget]=[]) -> None:
        """
        Fetches dependencies for the specified targets. This should be called prior to configure the project's graph with ``configure_graph()``.

        :param targets: The targets for which to fetch dependencies. Defaults to all targets.
        """
        targets = targets or self.all_targets()
        unique_deps = set()
        for target in targets:
            unique_deps.update(target.dependent_libraries)
        G_LOGGER.info(f"Fetching dependencies: {[dep.dependency for dep in unique_deps]}")

        for dep_lib in unique_deps:
            include_dirs = dep_lib.dependency.setup()
            self.files.add_include_dir(dep_lib.dependency.header_dir)
            [self.files.add_include_dir(dir) for dir in include_dirs]
            # Add all Library targets to the file manager's graph, since they are independent of profiles
            self.files.graph.add(dep_lib.library)
            G_LOGGER.verbose(f"Adding {dep_lib.library} to file manager.")


    # TODO: Add targets option here
    def configure_graph(self, targets: List[ProjectTarget]=[], profile_names: List[str]=[]) -> None:
        """
        Configures the project's build graph. This must be called prior to configuring a backend with ``configure_backend``.

        :param targets: The targets for which to configure the graph. Defaults to all targets.
        :param profile_names: The names of profiles for which to configure the graph. Defaults to all profiles.
        """
        targets = targets or self.all_targets()
        profile_names = profile_names or self.all_profile_names()

        # Scan for headers and propagate libs
        self.files.scan_all()

        for profile in self.profiles.values():
            profile.configure_libraries()

        # Combine the source graph from file manager and the various profile graphs
        def combined_graph():
            all_nodes = [target[prof_name] for target in targets for prof_name in profile_names]
            for node in all_nodes:
                all_nodes.extend(node.inputs)
            return Graph(set(all_nodes))

        self.graph = combined_graph()


    def configure_backend(self, BackendType: type=RBuildBackend) -> None:
        """
        Configure the project for build using the specified backend type. This includes generating any build configuration files required by this project's backend. This must be called prior to building.

        :param BackendType: The type of backend to use. Since SBuildr is a meta-build system, it can support multiple backends to perform builds. For example, RBuild (i.e. ``sbuildr.backends.RBuildBackend``) can be used for fast incremental builds. Note that this should be a type rather than an instance of a backend.
        """
        if not self.graph:
            G_LOGGER.critical(f"Project graph has not been configured. Please call `configure_graph()` prior to configuring a backend")

        self.backend = BackendType(self.build_dir)
        self.files.mkdir(self.build_dir)
        self.backend.configure(self.graph)


    def build(self, targets: List[ProjectTarget]=[], profile_names: List[str]=[]) -> float:
        """
        Builds the specified targets for this project. Configuration should be run prior to calling this function.

        :param targets: The targets to build. Defaults to all targets.
        :param profile_names: The profiles for which to build the targets. Defaults to all profiles.

        :returns: Time elapsed during the build.
        """
        G_LOGGER.info(f"Building targets: {[target.name for target in targets]} for profiles: {profile_names}")
        G_LOGGER.debug(f"Targets: {targets}")

        def select_nodes(targets: List[ProjectTarget], profile_names: List[str]) -> List[Node]:
            # Create all required profile build directories and populate nodes.
            nodes = []
            for prof_name in profile_names:
                if prof_name not in self.profiles:
                    G_LOGGER.critical(f"Profile {prof_name} does not exist in the project. Available profiles: {self.all_profile_names()}")
                # Populate nodes.
                for target in targets:
                    if prof_name in target:
                        node = target[prof_name]
                        G_LOGGER.verbose(f"For target: {target}, profile: {prof_name}, found path: {node.path}")
                        nodes.append(node)
                    else:
                        G_LOGGER.debug(f"Skipping target: {target.name} for profile: {prof_name}, as it does not exist.")
            return nodes

        targets = targets or self.all_targets()
        profile_names = profile_names or self.all_profile_names()

        # Create all required build directories.
        self.files.mkdir(self.common_objs_build_dir)
        profile_build_dirs = [self.profiles[prof_name].build_dir for prof_name in profile_names]
        [self.files.mkdir(dir) for dir in profile_build_dirs]
        G_LOGGER.verbose(f"Created build directories: {self.common_objs_build_dir}, {profile_build_dirs}")

        nodes = select_nodes(targets, profile_names)
        if not nodes:
            return

        if not self.backend:
            G_LOGGER.critical(f"Backend has not been configured. Please call `configure_backend()` prior to attempting to build")
        status, time_elapsed = self.backend.build(nodes)
        if status.returncode:
            G_LOGGER.critical(f"Failed with:\n{utils.subprocess_output(status)}\nReconfiguring the project or running a clean build may resolve this.")
        G_LOGGER.info(f"Built {plural('target', len(targets))} for {plural('profile', len(profile_names))} in {time_elapsed} seconds.")
        return time_elapsed


    # Sets up the environment correctly to be able to run the specified linked node.
    # TODO: Refactor into separate file with run() that does platform independent env vars.
    def _run_linked_node(self, node: LinkedNode, *args, **kwargs) -> subprocess.CompletedProcess:
        loader_path = os.environ[paths.loader_path_env_var()]
        G_LOGGER.verbose(f"Running linked node: {node}")
        for lib_dir in node.lib_dirs:
            loader_path += f"{os.pathsep}{lib_dir}"
        G_LOGGER.debug(f"Using loader paths: {loader_path}")
        G_LOGGER.log(f"{paths.loader_path_env_var()}={loader_path} {node.path}\n", color=logger.Color.GREEN)
        return subprocess.run([node.path], *args, env={paths.loader_path_env_var(): loader_path}, **kwargs)


    # TODO(0): Docstring
    def run(self, targets: List[ProjectTarget], profile_names: List[str]=[]):
        """
        Runs targets from this project.
        """
        for target in targets:
            if target.name not in self.executables:
                G_LOGGER.critical(f"Could not find target: {target.name} in project executables. Note: Available executables are: {list(self.executables.keys())}")

        def run_target(target: ProjectTarget, prof_name: str):
            G_LOGGER.log(f"\nRunning target: {target}, for profile: {prof_name}", color=logger.Color.GREEN)
            status = self._run_linked_node(target[prof_name])
            if result.returncode:
                G_LOGGER.critical(f"Failed to run. Reconfiguring the project or running a clean build may resolve this.")

        for prof_name in profile_names:
            G_LOGGER.log(f"\n{utils.wrap_str(f' Profile: {prof_name} ')}", color=logger.Color.GREEN)
            for target in targets:
                run_target(target, prof_name)


    def test_targets(self) -> List[ProjectTarget]:
        """
        Returns all targets in this project that are tests.

        :returns: A list of targets.
        """
        return list(self.tests.values())


    # TODO(0): Docstring
    def run_tests(self, targets: List[ProjectTarget]=[], profile_names: List[str]=[]):
        """
        Run tests from this project. Runs all tests from the project for all profiles by default.
        """
        for target in targets:
            if target.name not in self.tests:
                G_LOGGER.critical(f"Could not find test: {target.name} in project.\n\tAvailable tests:\n\t\t{list(self.tests.keys())}")

        tests = targets or self.test_targets()
        profile_names = profile_names or self.all_profile_names()
        if not tests:
            G_LOGGER.warning(f"No tests found. Have you registered tests using project.test()?")
            return

        class TestResult:
            def __init__(self):
                self.failed = 0
                self.passed = 0

        def run_test(test, prof_name):
            G_LOGGER.log(f"\nRunning test: {test}, for profile: {prof_name}", color=logger.Color.GREEN)
            status = self._run_linked_node(test[prof_name])
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


    def install_targets(self) -> List[ProjectTarget]:
        """
        Returns all targets that this project can install.

        :returns: A list of targets.
        """
        return [target for target in self.all_targets() if not target.internal]


    def install_profile(self) -> str:
        """
        Returns the name of the profile for which this project will install targets.
        """
        return "release"


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
        targets = targets or self.install_targets()
        profile_names = profile_names or [self.install_profile()]
        headers = [self.find(header) for header in headers] or list(self.public_headers)

        if dry_run:
            G_LOGGER.warning(f"Install dry-run, will not copy files.")

        def install_target(target, prof_name):
            node = target[prof_name]
            install_dir = library_install_path if target.is_lib else executable_install_path
            install_path = os.path.join(install_dir, node.basename)
            if dry_run:
                G_LOGGER.info(f"Would install target: {node.basename} to {install_path}")
            else:
                if utils.copy_path(node.path, install_path):
                    G_LOGGER.info(f"Installed target: {node.basename} to {install_path}")

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
        targets = targets or [target for target in self.all_targets() if not target.internal]
        profile_names = profile_names or ["release"]
        headers = [self.find(header) for header in headers] or list(self.public_headers)

        if dry_run:
            G_LOGGER.warning(f"Uninstall dry-run, will not remove files.")

        def uninstall_target(target, prof_name):
            node = target[prof_name]
            uninstall_dir = library_install_path if target.is_lib else executable_install_path
            uninstall_path = os.path.join(uninstall_dir, node.basename)
            if dry_run:
                G_LOGGER.info(f"Would remove target: {node.basename} from {uninstall_path}")
            else:
                os.remove(uninstall_path)
                G_LOGGER.info(f"Uninstalled target: {node.basename} from {uninstall_path}")

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
            profile_names = profile_names or self.all_profile_names()
            to_remove = [self.profiles[prof_name].build_dir for prof_name in profile_names]
            G_LOGGER.info(f"Cleaning targets for profiles: {prof_names}")
        # Remove
        for path in to_remove:
            if dry_run:
                G_LOGGER.info(f"Would remove: {path}")
            else:
                project.files.rm(path)
