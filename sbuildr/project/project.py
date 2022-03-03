import copy
import inspect
import os
import pickle
import subprocess
from collections import defaultdict
from typing import Dict, List, Set, Union

from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.dependencies.dependency import Dependency, DependencyLibrary
from sbuildr.graph.graph import Graph
from sbuildr.graph.node import CompiledNode, Library, LinkedNode, Node
from sbuildr.logger import G_LOGGER, Color, plural
from sbuildr.misc import paths, utils
from sbuildr.project.file_manager import FileManager
from sbuildr.project.profile import Profile
from sbuildr.project.target import ProjectTarget
from sbuildr.tools import compiler, linker
from sbuildr.tools.flags import BuildFlags


class Project(object):
    DEFAULT_SAVED_PROJECT_NAME = "project.sbuildr"
    PROJECT_API_VERSION = 1
    """
    Represents a project. Projects include two default profiles with the following configuration:
    ``release``: ``BuildFlags().O(3).std(17).march("native").fpic()``
    ``debug``: ``BuildFlags().O(0).std(17).debug().fpic().define("S_DEBUG")``, attaches file suffix "_debug"
    These can be overridden using the ``profile()`` function.

    :param root: The path to the root directory for this project. All directories and files within the root directory are considered during searches for files. If no root directory is provided, defaults to the containing directory of the script calling this constructor.
    :param dirs: Additional directories outside the root directory that are part of the project. These directories and all contents will be considered during searches for files.
    :param build_dir: The build directory to use. If no build directory is provided, a directory named 'build' is created in the root directory.
    """

    def __init__(self, root: str = None, dirs: Set[str] = set(), build_dir: str = None):
        self.PROJECT_API_VERSION = Project.PROJECT_API_VERSION
        # The assumption is that the caller of the init function is the SBuildr file for the build.
        config_file = os.path.abspath(inspect.stack()[1][0].f_code.co_filename)
        # Keep track of all files present in project dirs. Since dirs is a set, files is guaranteed
        # to contain no duplicates as well.
        self.files = FileManager(root or os.path.abspath(os.path.dirname(config_file)), dirs)
        # The build directory will be writable, and excluded when the FileManager is searching for paths.
        self.build_dir = self.files.add_writable_dir(
            self.files.add_exclude_dir(build_dir or os.path.join(self.files.root_dir, "build"))
        )
        # TODO: Make this a parameter?
        self.common_build_dir = os.path.join(self.build_dir, "common")
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
        # Files installed by this project.
        self.public_headers: Set[str] = {}
        # Dependencies required for the public headers.
        self.public_header_dependencies: List[Dependency] = []
        # Add default profiles
        self.profile(name="release", flags=BuildFlags().O(3).std(17).march("native").fpic())
        self.profile(
            name="debug", flags=BuildFlags().O(0).std(17).debug().fpic().define("S_DEBUG"), file_suffix="_debug"
        )
        # A graph describing the entire project. This is typically not constructed until just before the build
        self.graph: Graph = None

    @staticmethod
    def load(path: str = None) -> "Project":
        f"""
        Load a project from the specified path.

        :param path: The path from which to load the project. Defaults to {os.path.abspath(os.path.join("build", Project.DEFAULT_SAVED_PROJECT_NAME))}

        :returns: The loaded project.
        """
        path = path or os.path.abspath(os.path.join("build", Project.DEFAULT_SAVED_PROJECT_NAME))
        G_LOGGER.debug(f"Loading project from {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    def export(self, path: str = None) -> None:
        f"""
        Export this project to the specified path. This enables the project to be used with SBuildr's dependency management system, as well as with the command-line sbuildr utility.

        :param path: The path at which to export the project. Defaults to {Project.DEFAULT_SAVED_PROJECT_NAME} in the project's build directory.
        """
        path = path or os.path.join(self.build_dir, Project.DEFAULT_SAVED_PROJECT_NAME)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        G_LOGGER.info(f"Exporting project to {path}")
        with open(path, "wb") as f:
            pickle.dump(self, f)

    def __contains__(self, target_name: str) -> bool:
        return any([tgt.name == target_name for tgt in self.all_targets()])

    def all_targets(self):
        return list(self.libraries.values()) + list(self.executables.values()) + list(self.tests.values())

    def all_profile_names(self) -> List[str]:
        return list(self.profiles.keys())

    # TODO: Test header only libraries with depends
    def _target(
        self,
        name: str,
        ext_path: str,
        sources: List[str],
        flags: BuildFlags,
        libs: List[Union[DependencyLibrary, ProjectTarget, Library]],
        compiler: compiler.Compiler,
        include_dirs: List[str],
        linker: linker.Linker,
        depends: List[Dependency],
        internal: bool,
        is_lib: bool,
    ) -> ProjectTarget:

        if not all(
            [
                isinstance(lib, ProjectTarget) or isinstance(lib, Library) or isinstance(lib, DependencyLibrary)
                for lib in libs
            ]
        ):
            G_LOGGER.critical(
                f"Libraries must be instances of either sbuildr.Library, sbuildr.dependencies.DependencyLibrary or sbuildr.ProjectTarget"
            )

        if os.path.basename(ext_path) != ext_path:
            G_LOGGER.critical(
                f"Target: {ext_path} looks like a path. Target names should not contain characters that are unsupported by the filesystem."
            )

        dependencies: List[Dependency] = [] + depends  # Create copy
        for lib in libs:
            if isinstance(lib, DependencyLibrary):
                dependencies.append(lib.dependency)
                # Add all Library targets from dependencies to the file manager's graph, since they are independent of profiles
                # TODO: Add `library` function to FileManager
                self.files.graph.add(lib.library)
                G_LOGGER.verbose(f"Adding {lib.library} to file manager.")
        # Inherit dependencies from any input libraries as well
        [dependencies.extend(lib.dependencies) for lib in libs if isinstance(lib, ProjectTarget)]

        libs: List[Union[ProjectTarget, Library]] = [
            lib.library if isinstance(lib, DependencyLibrary) else lib for lib in libs
        ]

        source_nodes: List[CompiledNode] = [self.files.source(path) for path in sources]
        G_LOGGER.verbose(f"For sources: {sources}, found source paths: {source_nodes}")

        target = ProjectTarget(name=name, internal=internal, is_lib=is_lib, dependencies=dependencies)
        for profile_name, profile in self.profiles.items():
            # Convert all libraries to nodes. These will be inputs to the target.
            # Profile will later convert them to library names and directories.
            lib_nodes: List[Library] = [lib[profile_name] if isinstance(lib, ProjectTarget) else lib for lib in libs]
            input_nodes = [lib for lib in lib_nodes]
            G_LOGGER.verbose(f"Library inputs for target: {name} are: {input_nodes}")

            # Per-target flags always overwrite profile flags.
            flags = profile.flags + flags

            # First, add or retrieve object nodes for each source.
            for source_node in source_nodes:
                obj_path = os.path.join(
                    self.common_build_dir, f"{os.path.splitext(os.path.basename(source_node.path))[0]}.o"
                )
                # User defined includes are always prepended the ones deduced for SourceNodes.
                obj_node = CompiledNode(obj_path, source_node, compiler, include_dirs, flags)
                input_nodes.append(profile.graph.add(obj_node))

            # Hard links are needed because during linkage, the library must have a clean name.
            hashed_path = os.path.join(self.common_build_dir, ext_path)
            path = os.path.join(profile.build_dir, paths.insert_suffix(ext_path, profile.suffix))
            target[profile_name] = profile.graph.add(
                LinkedNode(path, input_nodes, linker, hashed_path=hashed_path, flags=flags)
            )
            G_LOGGER.debug(
                f"Adding target: {name}, with hashed path: {hashed_path}, public path: {path} to profile: {profile_name}"
            )
        return target

    # Both of these functions will modify name before passing it to profile so that the filename is correct.
    def executable(
        self,
        name: str,
        sources: List[str],
        flags: BuildFlags = BuildFlags(),
        libs: List[Union[DependencyLibrary, ProjectTarget, Library]] = [],
        compiler: compiler.Compiler = compiler.clang,
        include_dirs: List[str] = [],
        linker: linker.Linker = linker.clang,
        depends: List[Dependency] = [],
        internal=False,
    ) -> ProjectTarget:
        """
        Adds an executable target to all profiles within this project.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either :class:`ProjectTarget` s, :class:`DependencyLibrary` s or :class:`Library` s.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param depends: Any additional dependencies not already captured in libs. This may include header only packages for example.
        :param internal: Whether this target is internal to the project, in which case it will not be installed.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.executables[name] = self._target(
            name,
            paths.name_to_execname(name),
            sources,
            flags,
            libs,
            compiler,
            include_dirs,
            linker,
            depends,
            internal,
            is_lib=False,
        )
        return self.executables[name]

    def test(
        self,
        name: str,
        sources: List[str],
        flags: BuildFlags = BuildFlags(),
        libs: List[Union[DependencyLibrary, ProjectTarget, Library]] = [],
        compiler: compiler.Compiler = compiler.clang,
        include_dirs: List[str] = [],
        linker: linker.Linker = linker.clang,
        depends: List[Dependency] = [],
    ) -> ProjectTarget:
        """
        Adds an executable target to all profiles within this project. Test targets can be automatically built and run by using the ``test`` command on the CLI.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either :class:`ProjectTarget` s, :class:`DependencyLibrary` s or :class:`Library` s.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param depends: Any additional dependencies not already captured in libs. This may include header only packages for example.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.tests[name] = self._target(
            name,
            paths.name_to_execname(name),
            sources,
            flags,
            libs,
            compiler,
            include_dirs,
            linker,
            depends,
            internal=True,
            is_lib=False,
        )
        return self.tests[name]

    def library(
        self,
        name: str,
        sources: List[str],
        flags: BuildFlags = BuildFlags(),
        libs: List[Union[DependencyLibrary, ProjectTarget, Library]] = [],
        compiler: compiler.Compiler = compiler.clang,
        include_dirs: List[str] = [],
        linker: linker.Linker = linker.clang,
        depends: List[Dependency] = [],
        internal=False,
    ) -> ProjectTarget:
        """
        Adds a library target to all profiles within this project.

        :param name: The name of the target. This should NOT include platform-dependent extensions.
        :param sources: A list of names or paths of source files to include in this target.
        :param flags: Compiler and linker flags. See sbuildr.BuildFlags for details.
        :param libs: A list containing either :class:`ProjectTarget` s, :class:`DependencyLibrary` s or :class:`Library` s.
        :param compiler: The compiler to use for this target. Defaults to clang.
        :param include_dirs: A list of paths for preprocessor include directories. These directories take precedence over automatically deduced include directories.
        :param linker: The linker to use for this target. Defaults to clang.
        :param depends: Any additional dependencies not already captured in libs. This may include header only packages for example.
        :param internal: Whether this target is internal to the project, in which case it will not be installed.

        :returns: :class:`sbuildr.project.target.ProjectTarget`
        """
        self.libraries[name] = self._target(
            name,
            paths.name_to_libname(name),
            sources,
            flags + BuildFlags()._enable_shared(),
            libs,
            compiler,
            include_dirs,
            linker,
            depends,
            internal,
            is_lib=True,
        )
        return self.libraries[name]

    # Returns a profile if it exists, otherwise creates a new one and returns it.
    def profile(
        self, name: str, flags: BuildFlags = BuildFlags(), build_dir: str = None, file_suffix: str = ""
    ) -> Profile:
        f"""
        Returns or creates a profile with the specified parameters.

        :param name: The name of this profile.
        :param flags: The flags to use for this profile. These will be applied to all targets for this profile. Per-target flags always take precedence.
        :param build_dir: The directory to use for build artifacts. Defaults to {os.path.join(self.build_dir, name)}
        :param file_suffix: A file suffix to attach to all artifacts generated for this profile. For example, the default debug profile attaches a ``_debug`` suffix to all library and executable names.

        :returns: :class:`sbuildr.Profile`
        """
        if name not in self.profiles:
            build_dir = self.files.add_writable_dir(
                self.files.add_exclude_dir(os.path.abspath(build_dir or os.path.join(self.build_dir, name)))
            )
            G_LOGGER.verbose(f"Setting build directory for profile: {name} to: {build_dir}")
            self.profiles[name] = Profile(flags=flags, build_dir=build_dir, suffix=file_suffix)
        return self.profiles[name]

    def interfaces(self, headers: List[str], depends: List[Dependency] = []) -> List[str]:
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
                G_LOGGER.critical(
                    f"For installation target: {target}, found multiple installation candidates: {candidates}. Please provide a longer path to disambiguate."
                )
            discovered_paths.append(candidates[0])
        self.public_headers = set(discovered_paths)
        self.public_header_dependencies.extend(depends)
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
            G_LOGGER.critical(
                f"For path: {path}, found multiple candidates: {candidates}. Please provide a longer path to disambiguate."
            )
        return candidates[0]

    def configure(
        self, targets: List[ProjectTarget] = None, profile_names: List[str] = None, BackendType: type = RBuildBackend
    ) -> None:
        """
        Configure does 3 things:
        1. Finds dependencies for the specified targets. This involves potentially fetching and building dependencies if they do not exist in the cache.
        2. Configures the project's build graph after discovering libraries for targets. Before calling configure(), a target's libs/lib_dirs lists are not guaranteed to be complete.
        3. Configure the project for build using the specified backend type. This includes generating any build configuration files required by this project's backend.

        This function must be called prior to building.

        :param targets: The targets for which to configure the project. Defaults to all targets.
        :param profile_names: The names of profiles for which to configure the project. Defaults to all profiles.
        :param BackendType: The type of backend to use. Since SBuildr is a meta-build system, it can support multiple backends to perform builds. For example, RBuild (i.e. ``sbuildr.backends.RBuildBackend``) can be used for fast incremental builds. Note that this should be a type rather than an instance of a backend.
        """
        targets = utils.default_value(targets, self.all_targets())
        profile_names = utils.default_value(profile_names, self.all_profile_names())

        def find_dependencies():
            unique_deps: Set[Dependency] = set()
            for target in targets:
                unique_deps.update(target.dependencies)

            required_deps = self.public_header_dependencies + list(unique_deps)
            G_LOGGER.info(f"Fetching dependencies: {required_deps}")
            for dep in required_deps:
                meta = dep.setup()
                self.files.add_include_dir(dep.include_dir())
                [self.files.add_include_dir(dir) for dir in meta.include_dirs]

        def configure_graph():
            self.files.scan_all()
            for profile in self.profiles.values():
                profile.configure_libraries()

            def combined_graph():
                all_nodes = [target[prof_name] for target in targets for prof_name in profile_names]
                for node in all_nodes:
                    all_nodes.extend(node.inputs)
                graph = Graph(set(all_nodes))

                # Need to rename all the files in the build graph so that they have hashes.
                for layer in graph.layers():
                    for node in layer:
                        if isinstance(node, CompiledNode):
                            signature = node.compiler.signature(node.inputs[0].path, node.include_dirs, node.flags)
                            node.path = paths.insert_suffix(node.path, f".{signature}")
                        elif isinstance(node, LinkedNode):
                            signature = node.linker.signature(
                                [inp.path for inp in node.inputs], node.libs, node.lib_dirs, node.flags
                            )
                            node.hashed_path = paths.insert_suffix(node.hashed_path, f".{signature}")

                return graph

            self.graph = combined_graph()

        def configure_backend():
            self.backend = BackendType(self.build_dir)
            self.files.mkdir(self.build_dir)
            self.backend.configure(self.graph)

        find_dependencies()
        configure_graph()
        configure_backend()

    def build(self, targets: List[ProjectTarget] = None, profile_names: List[str] = None) -> float:
        """
        Builds the specified targets for this project. Configuration should be run prior to calling this function.

        :param targets: The targets to build. Defaults to all targets.
        :param profile_names: The profiles for which to build the targets. Defaults to all profiles.

        :returns: Time elapsed during the build.
        """
        targets = utils.default_value(targets, self.all_targets())
        profile_names = utils.default_value(profile_names, self.all_profile_names())
        G_LOGGER.info(f"Building targets: {[target.name for target in targets]} for profiles: {profile_names}")
        G_LOGGER.debug(f"Targets: {targets}")

        def select_nodes(targets: List[ProjectTarget], profile_names: List[str]) -> List[Node]:
            # Create all required profile build directories and populate nodes.
            nodes = []
            for prof_name in profile_names:
                if prof_name not in self.profiles:
                    G_LOGGER.critical(
                        f"Profile {prof_name} does not exist in the project. Available profiles: {self.all_profile_names()}"
                    )
                # Populate nodes.
                for target in targets:
                    if prof_name in target:
                        node = target[prof_name]
                        G_LOGGER.verbose(f"For target: {target}, profile: {prof_name}, found path: {node.path}")
                        nodes.append(node)
                    else:
                        G_LOGGER.debug(
                            f"Skipping target: {target.name} for profile: {prof_name}, as it does not exist."
                        )
            return nodes

        nodes = select_nodes(targets, profile_names)
        if not nodes:
            return

        # Create all required build directories.
        self.files.mkdir(self.common_build_dir)
        profile_build_dirs = [self.profiles[prof_name].build_dir for prof_name in profile_names]
        [self.files.mkdir(dir) for dir in profile_build_dirs]
        G_LOGGER.verbose(f"Created build directories: {self.common_build_dir}, {profile_build_dirs}")

        if not self.backend:
            G_LOGGER.critical(
                f"Backend has not been configured. Please call `configure()` prior to attempting to build"
            )
        status, time_elapsed = self.backend.build(nodes)
        if status.returncode:
            G_LOGGER.critical(
                f"Failed with to build. Reconfiguring the project or running a clean build may resolve this."
            )
        G_LOGGER.info(
            f"Built {plural('target', len(targets))} for {plural('profile', len(profile_names))} in {time_elapsed} seconds."
        )
        return time_elapsed

    # Sets up the environment correctly to be able to run the specified linked node.
    # TODO: Refactor into separate file with run() that does platform independent env vars.
    def _run_linked_node(self, node: LinkedNode, *args, **kwargs) -> subprocess.CompletedProcess:
        loader_path = os.environ.get(paths.loader_path_env_var(), "")
        G_LOGGER.verbose(f"Running linked node: {node}")
        for lib_dir in node.lib_dirs:
            loader_path += f"{os.path.pathsep}{lib_dir}"
        G_LOGGER.debug(f"Using loader paths: {loader_path}")
        G_LOGGER.log(f"{paths.loader_path_env_var()}={loader_path} {node.path}\n", colors=[Color.BOLD, Color.GREEN])
        env = copy.copy(os.environ)
        env[paths.loader_path_env_var()] = loader_path
        return subprocess.run([node.path], *args, env=env, **kwargs)

    def run(self, targets: List[ProjectTarget], profile_names: List[str] = []) -> None:
        """
        Runs targets from this project.

        :param targets: The targets to run.
        :param profile_names: The profiles for which to run the targets.
        """
        for target in targets:
            if target.name not in self.executables:
                G_LOGGER.critical(
                    f"Could not find target: {target.name} in project executables. Note: Available executables are: {list(self.executables.keys())}"
                )

        def run_target(target: ProjectTarget, prof_name: str):
            G_LOGGER.log(f"\nRunning target: {target}, for profile: {prof_name}", colors=[Color.BOLD, Color.GREEN])
            status = self._run_linked_node(target[prof_name])
            if status.returncode:
                G_LOGGER.critical(
                    f"Failed to run. Reconfiguring the project or running a clean build may resolve this."
                )

        for prof_name in profile_names:
            G_LOGGER.log(f"\n{utils.wrap_str(f' Profile: {prof_name} ')}", colors=[Color.BOLD, Color.GREEN])
            for target in targets:
                run_target(target, prof_name)

    def test_targets(self) -> List[ProjectTarget]:
        """
        Returns all targets in this project that are tests.

        :returns: A list of targets.
        """
        return list(self.tests.values())

    def run_tests(self, targets: List[ProjectTarget] = None, profile_names: List[str] = None):
        """
        Run tests from this project. Runs all tests from the project for all profiles by default.

        :param targets: The test targets to run. Raises an exception if the target is not a test target.
        :param profile_names: The profiles for which to run the tests. Defaults to all profiles.
        """
        for target in targets:
            if target.name not in self.tests:
                G_LOGGER.critical(
                    f"Could not find test: {target.name} in project.\n\tAvailable tests:\n\t\t{list(self.tests.keys())}"
                )

        tests = utils.default_value(targets, self.test_targets())
        profile_names = utils.default_value(profile_names, self.all_profile_names())
        if not tests:
            G_LOGGER.warning(f"No tests found. Have you registered tests using project.test()?")
            return

        class TestResult:
            def __init__(self):
                self.failed = 0
                self.passed = 0

        def run_test(test, prof_name):
            G_LOGGER.log(f"\nRunning test: {test}, for profile: {prof_name}", colors=[Color.BOLD, Color.GREEN])
            status = self._run_linked_node(test[prof_name])
            if status.returncode:
                G_LOGGER.log(
                    f"\nFAILED {test}, for profile: {prof_name}:\n{test[prof_name].path}",
                    colors=[Color.BOLD, Color.RED],
                )
                test_results[prof_name].failed += 1
                failed_targets[prof_name].add(test[prof_name].name)
            else:
                G_LOGGER.log(f"\nPASSED {test}", colors=[Color.BOLD, Color.GREEN])
                test_results[prof_name].passed += 1

        test_results = defaultdict(TestResult)
        failed_targets = defaultdict(set)
        for prof_name in profile_names:
            G_LOGGER.log(f"\n{utils.wrap_str(f' Profile: {prof_name} ')}", colors=[Color.BOLD, Color.GREEN])
            for test in tests:
                run_test(test, prof_name)

        # Display summary
        G_LOGGER.log(f"\n{utils.wrap_str(f' Test Results Summary ')}\n", colors=[Color.BOLD, Color.GREEN])
        for prof_name, result in test_results.items():
            if result.passed or result.failed:
                G_LOGGER.log(f"Profile: {prof_name}", colors=[Color.BOLD, Color.GREEN])
                if result.passed:
                    G_LOGGER.log(f"\tPASSED {plural('test', result.passed)}", colors=[Color.BOLD, Color.GREEN])
                if result.failed:
                    G_LOGGER.log(
                        f"\tFAILED {plural('test', result.failed)}: {failed_targets[prof_name]}",
                        colors=[Color.BOLD, Color.RED],
                    )

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

    def install(
        self,
        targets: List[ProjectTarget] = None,
        profile_names: List[str] = None,
        headers: List[str] = None,
        header_install_path: str = paths.default_header_install_path(),
        library_install_path: str = paths.default_library_install_path(),
        executable_install_path: str = paths.default_executable_install_path(),
        dry_run: bool = True,
    ):
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
        targets = utils.default_value(targets, self.install_targets())
        profile_names = utils.default_value(profile_names, [self.install_profile()])
        headers = [self.find(header) for header in headers] if headers is not None else list(self.public_headers)

        if dry_run:
            G_LOGGER.warning(f"Install dry-run, will not copy files.")

        def install_target(target, prof_name):
            node: LinkedNode = target[prof_name]
            install_dir = library_install_path if target.is_lib else executable_install_path
            install_path = os.path.join(install_dir, os.path.basename(node.path))
            if dry_run:
                G_LOGGER.info(f"Would install target: {node.path} to {install_path}")
            else:
                if utils.copy_path(node.path, install_path):
                    G_LOGGER.info(f"Installed target: {node.path} to {install_path}")

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

    def uninstall(
        self,
        targets: List[ProjectTarget] = None,
        profile_names: List[str] = None,
        headers: List[str] = None,
        header_install_path: str = paths.default_header_install_path(),
        library_install_path: str = paths.default_library_install_path(),
        executable_install_path: str = paths.default_executable_install_path(),
        dry_run: bool = True,
    ):
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
        targets = utils.default_value(targets, [target for target in self.all_targets() if not target.internal])
        profile_names = utils.default_value(profile_names, ["release"])
        headers = [self.find(header) for header in headers] if headers is not None else list(self.public_headers)

        if dry_run:
            G_LOGGER.warning(f"Uninstall dry-run, will not remove files.")

        def uninstall_target(target, prof_name):
            node: LinkedNode = target[prof_name]
            uninstall_dir = library_install_path if target.is_lib else executable_install_path
            uninstall_path = os.path.join(uninstall_dir, os.path.basename(node.path))
            if dry_run:
                G_LOGGER.info(f"Would remove target: {node.path} from {uninstall_path}")
            else:
                os.remove(uninstall_path)
                G_LOGGER.info(f"Uninstalled target: {node.path} from {uninstall_path}")

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

    def clean(self, nuke: bool = False, dry_run: bool = True):
        """
        Removes build directories and project artifacts.

        :param nuke: Whether to remove all build directories associated with the project, including profile build directories.
        :param dry_run: Whether this is a dry-run, in which case SBuildr will only display which directories would be removed rather than removing them. Defaults to True.
        """
        # TODO(3): Add per-target cleaning.
        to_remove = []
        if dry_run:
            G_LOGGER.warning(f"Clean dry-run, will not remove files.")

        # By default, cleans all targets for all profiles.
        to_remove = [self.profiles[prof_name].build_dir for prof_name in self.all_profile_names()] + [
            self.common_build_dir
        ]
        G_LOGGER.info(f"Cleaning targets for profiles: {self.all_profile_names()}")
        if nuke:
            # The nuclear option
            to_remove += [self.build_dir]
            G_LOGGER.info(f"Initiating Nuclear Protocol!")
        # Remove
        for path in to_remove:
            if dry_run:
                G_LOGGER.info(f"Would remove: {path}")
            else:
                self.files.rm(path)
