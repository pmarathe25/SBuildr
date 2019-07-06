from sbuildr.generator.rbuild import RBuildGenerator
from sbuildr.project.target import ProjectTarget
from sbuildr.project.project import Project
from sbuildr.logger import G_LOGGER, plural
from sbuildr.graph.node import Node
import sbuildr.logger as logger

from typing import List, Tuple
import subprocess
import argparse
import shutil
import sys
import os

# Set up a special parser just to intercept -v/-vv. This will not intercept -h, so we duplicate the options
# in the cli() parser.
verbosity_parser = argparse.ArgumentParser(add_help=False)
verbosity_parser.add_argument("-v", "--verbose", action="store_true")
verbosity_parser.add_argument("-vv", "--very-verbose", action="store_true")

args, _ = verbosity_parser.parse_known_args()
if args.very_verbose:
    G_LOGGER.verbosity = logger.Verbosity.VERBOSE
elif args.verbose:
    G_LOGGER.verbosity = logger.Verbosity.DEBUG

# Sets up the the command-line interface for the given project/generator combination.
# When no profile(s) are specified, default_profile will be used.
def cli(project: Project, GeneratorType: type=RBuildGenerator, default_profiles=["debug", "release"]):
    """
    Adds the SBuildr command-line interface to the Python script invoking this function. For detailed usage information, you can run the Python code invoking this function with ``--help``.

    :param project: The project that the CLI will interface with.
    :param GeneratorType: The type of generator to use for generating configuration files. Since SBuildr is a meta-build system, it can support multiple backends to perform builds. For example, RBuild (i.e. ``sbuildr.generator.RBuildGenerator``) can be used for fast incremental builds.
    :param default_profiles: Names of default profiles. These are the profiles the CLI will target when none are explicitly specified via the command-line.
    """
    generator = GeneratorType(project)

    def needs_configure(func, *args, **kwargs):
        def wrapper(*args, **kwargs):
            if generator.needs_configure():
                G_LOGGER.warning(f"'{func.__name__}' requires the project to be configured, but project has either not been configured yet, or configuration is outdated. Running configuration now.")
                configure(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper

    def _wrap_str(inp: str, wrap: str='='):
        terminal_width, _ = shutil.get_terminal_size()
        return inp.center(terminal_width, wrap)

    # Returns the captured output
    # TODO: Subprocess management needs to be centralized somewhere.
    def _check_returncode(result: subprocess.CompletedProcess) -> str:
        output = f"{_wrap_str(' Captured stdout ')}\n{result.stdout.decode(sys.stdout.encoding)}\n{_wrap_str(' Captured stderr ')}\n{result.stderr.decode(sys.stdout.encoding)}"
        if result.returncode:
            G_LOGGER.critical(f"Failed with:\n{output}\nReconfiguring the project or running a clean build may resolve this.")
        return output

    def _all_targets() -> List[ProjectTarget]:
        return list(project.libraries.values()) + list(project.executables.values())

    # Given target names, returns the corresponding targets.
    # Falls back to returning all targets.
    def _select_targets(args) -> List[ProjectTarget]:
        targets = []
        for tgt_name in args.targets:
            if tgt_name not in project:
                G_LOGGER.critical(f"Could not find target: {tgt_name} in project.\n\tAvailable libraries:\n\t\t{list(project.libraries.keys())}\n\tAvailable executables:\n\t\t{list(project.executables.keys())}")
            if tgt_name in project.libraries:
                G_LOGGER.verbose(f"Found library for target: {tgt_name}")
                targets.append(project.libraries[tgt_name])
            if tgt_name in project.executables:
                G_LOGGER.verbose(f"Found executable for target: {tgt_name}")
                targets.append(project.executables[tgt_name])
            if tgt_name in project.executables and tgt_name in project.libraries:
                G_LOGGER.warning(f"Target: {tgt_name} refers to both an executable and a library. Selecting both.")
        return targets

    def _select_test_targets(args) -> List[ProjectTarget]:
        targets = []
        for test_name in args.targets:
            if test_name not in project.tests:
                G_LOGGER.critical(f"Could not find test: {test_name} in project.\n\tAvailable tests:\n\t\t{list(project.tests.keys())}")
            targets.append(project.tests[test_name])
        return targets or list(project.tests.values())

    # Given argparse's args struct, parses out profile flags, and returns a list of profile names included.
    # Falls back to returning the default profile.
    def _select_profile_names(args) -> List[str]:
        return [prof_name for prof_name in project.profiles.keys() if getattr(args, prof_name)]

    def _select_nodes(targets: List[ProjectTarget], prof_names: List[str]) -> List[Node]:
        nodes = []
        # Create all required profile build directories and populate nodes.
        for prof_name in prof_names:
            if prof_name not in project.profiles:
                G_LOGGER.critical(f"Profile {prof_name} does not exist in the project. Available profiles: {list(project.profiles.keys())}")
            project.files.mkdir(project.profiles[prof_name].build_dir)
            # Populate nodes.
            for target in targets:
                if prof_name in target:
                    node = target[prof_name]
                    G_LOGGER.verbose(f"For target: {target}, profile: {prof_name}, found path: {node.path}")
                    nodes.append(node)
                else:
                    G_LOGGER.debug(f"Skipping target: {target.name} for profile: {prof_name}, as it does not exist.")
        return nodes

    def _build_nodes(nodes: List[Node]) -> float:
        status, time_elapsed = generator.build(nodes)
        _check_returncode(status)
        return time_elapsed

    def _build_targets(targets: List[ProjectTarget], prof_names: List[str]):
        G_LOGGER.info(f"Building targets: {[target.name for target in targets]} for profiles: {prof_names}")
        G_LOGGER.debug(f"Targets: {targets}")

        time_elapsed = _build_nodes(_select_nodes(targets, prof_names))
        G_LOGGER.info(f"Built {plural('target', len(targets))} for {plural('profile', len(prof_names))} in {time_elapsed} seconds.")

    def help_targets(args):
        targets = _select_targets(args) or _all_targets()
        G_LOGGER.info(f"\n{_wrap_str(' Targets ')}")
        for target in targets:
            G_LOGGER.info(f"Target: {target}. Available Profiles:")
            for prof, node in target.items():
                G_LOGGER.info(f"\tProfile: {prof}. Path: {node.path}.")
                if node in project.installs:
                    G_LOGGER.info(f"\t\tInstalls to: {project.installs[node]}")
        G_LOGGER.info(f"\n{_wrap_str(' Paths ')}")
        for node, install_path in project.external_installs.items():
            G_LOGGER.info(f"Path: {node.path}")
            G_LOGGER.info(f"\t\tInstalls to: {install_path}")

    def configure(args):
        generator.generate()

    @needs_configure
    def build(args) -> Tuple[List[ProjectTarget], List[str]]:
        targets = _select_targets(args) or _all_targets()
        prof_names = _select_profile_names(args) or default_profiles
        _build_targets(targets, prof_names)

    @needs_configure
    def run(args):
        if args.target not in project.executables:
            G_LOGGER.critical(f"Could not find target: {args.target} in project executables. Note: Available executables are: {list(project.executables.keys())}")
        target = project.executables[args.target]
        prof_name = _select_profile_names(args)[0] or default_profiles
        _build_targets([target], [prof_name])
        G_LOGGER.log(f"\nRunning target: {target}, for profile: {prof_name}: {target[prof_name].path}", color=logger.Color.GREEN)
        G_LOGGER.log(_check_returncode(subprocess.run([target[prof_name].path], capture_output=True)))

    @needs_configure
    def tests(args):
        tests = _select_test_targets(args)
        prof_names = _select_profile_names(args) or default_profiles
        if not tests:
            G_LOGGER.warning(f"No tests found. Have you registered tests using project.test()?")
            return
        # Otherwise, build and run the specified tests
        _build_targets(tests, prof_names)
        for prof_name in prof_names:
            G_LOGGER.log(f"\n{_wrap_str(f' Profile: {prof_name} ')}", color=logger.Color.GREEN)
            for test_target in tests:
                G_LOGGER.log(f"\nRunning test: {test_target}, for profile: {prof_name}: {test_target[prof_name].path}", color=logger.Color.GREEN)
                status = subprocess.run([test_target[prof_name].path])
                if status.returncode:
                    G_LOGGER.log(f"\nFAILED {test_target}, for profile: {prof_name}:\n{test_target[prof_name].path}", color=logger.Color.PURPLE)
                else:
                    G_LOGGER.log(f"PASSED {test_target}", color=logger.Color.GREEN)

    # TODO: Need a wrapper that creates symlinks for version.
    # Copies src to dst
    def _copy_file(src, dst) -> bool:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            return True
        except PermissionError:
            G_LOGGER.error(f"Could not write to {dst}. Do you have sufficient privileges?")
            return False

    def _get_install_nodes(args):
        external_nodes, targets = [], []
        for tgt in args.targets:
            if tgt in project:
                targets.append(tgt)
            else:
                external_nodes.append(tgt)
        args.targets = targets
        # TODO: Maybe change this to only select all external nodes if no targets are specified.
        external_nodes = external_nodes or list(project.external_installs.keys())
        targets = _select_targets(args)
        # Targets may be unspecified, in which case we have to select nodes based on any specified profiles.
        prof_names = _select_profile_names(args) or (project.profile_installs.keys())
        nodes = _select_nodes(targets, prof_names)
        if not nodes:
            for prof_name in prof_names:
                nodes.extend(project.profile_installs[prof_name])
        return nodes, external_nodes

    # Add -f flag and --upgrade behavior should be to remove older versions.
    @needs_configure
    def install(args):
        nodes, external_nodes = _get_install_nodes(args)
        _build_nodes(nodes)

        for (node_list, install_dict) in [(nodes, project.installs), (external_nodes, project.external_installs)]:
            for node in node_list:
                if node not in install_dict:
                    G_LOGGER.warning(f"Could not find installation path for {node.name}, skipping.")
                else:
                    install_path = install_dict[node]
                    if _copy_file(node.path, install_path):
                        G_LOGGER.info(f"Installed file: {node.name} to {install_path}")

    def uninstall(args):
        nodes, external_nodes = _get_install_nodes(args)

        if not args.force:
            G_LOGGER.warning(f"Uninstall dry-run, will not remove files without -f/--force.")

        for (node_list, install_dict) in [(nodes, project.installs), (external_nodes, project.external_installs)]:
            for node in node_list:
                if node not in install_dict:
                    G_LOGGER.warning(f"Target: {node.name} is not designated as an installation target, will not uninstall.")
                install_path = install_dict[node]
                if args.force:
                    if os.path.exists(install_path):
                        G_LOGGER.info(f"Removing {install_path}")
                        os.remove(install_path)
                    else:
                        G_LOGGER.warning(f"{node.name} has not been installed (would be installed to {install_path}), skipping.")
                else:
                    G_LOGGER.info(f"Would remove: {install_path}")

    def clean(args):
        # TODO(3): Finish implementation, add per-target cleaning.
        to_remove = []
        if args.nuke:
            # The nuclear option
            to_remove = [project.build_dir]
            G_LOGGER.info(f"Initiating Nuclear Protocol!")
        else:
            # By default, cleans all targets for the default profile.
            prof_names = _select_profile_names(args) or default_profiles
            to_remove = [project.profiles[prof_name].build_dir for prof_name in prof_names]
            G_LOGGER.info(f"Cleaning targets for profiles: {prof_names}")
        # Remove
        for path in to_remove:
            project.files.rm(path)

    parser = argparse.ArgumentParser(description="Builds this project")
    parser.add_argument("-v", "--verbose", help="Enable verbose logging output", action="store_true")
    parser.add_argument("-vv", "--very-verbose", help="Enable very verbose logging output", action="store_true")

    def _add_profile_args(parser_like, verb: str):
        for prof_name in project.profiles.keys():
            parser_like.add_argument(f"--{prof_name}", help=f"{verb} targets for the {prof_name} profile", action="store_true")

    # By setting defaults, each subparser automatically invokes a function to execute it's actions.
    subparsers = parser.add_subparsers()

    # List
    help_targets_parser = subparsers.add_parser("targets", help="Display information about targets", description="Display information about the targets in this project")
    help_targets_parser.add_argument("targets", nargs='*', help="Targets to display. By default, displays help information for all targets.", default=[])
    help_targets_parser.set_defaults(func=help_targets)

    # Configure
    configure_parser = subparsers.add_parser("configure", help="Generate build configuration files", description="Generate a build configuration file for the project")
    configure_parser.set_defaults(func=configure)

    # Build
    build_parser = subparsers.add_parser("build", help="Build project targets", description="Build one or more project targets")
    build_parser.add_argument("targets", nargs='*', help="Targets to build. By default, builds all targets for the default profiles.", default=[])
    _add_profile_args(build_parser, "Build")
    build_parser.set_defaults(func=build)

    # Run
    run_parser = subparsers.add_parser("run", help="Run a project executable", description="Run a project executable")
    run_parser.add_argument("target", help="Target corresponding to an executable")
    run_profile_group = run_parser.add_mutually_exclusive_group()
    _add_profile_args(run_profile_group, "Run")
    run_parser.set_defaults(func=run)

    # Test
    tests_parser = subparsers.add_parser("tests", help="Run project tests", description="Run one or more project tests")
    tests_parser.add_argument("targets", nargs='*', help="Targets to test. By default, tests all targets for the default profiles.", default=[])
    _add_profile_args(tests_parser, "Test")
    tests_parser.set_defaults(func=tests)

    # Install
    install_parser = subparsers.add_parser("install", help="Install project targets", description="Install one or more project targets")
    install_parser.add_argument("targets", nargs='*', help="Targets to install. By default, installs all targets and paths specified.", default=[])
    _add_profile_args(install_parser, "Install")
    install_parser.set_defaults(func=install)

    # Uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall project targets", description="Uninstall one or more project targets")
    uninstall_parser.add_argument("-f", "--force", help="Remove targets. Without this flag, uninstall will only do a dry-run", action="store_true")
    uninstall_parser.add_argument("targets", nargs='*', help="Targets to uninstall. By default, uninstalls all targets and paths specified.", default=[])
    _add_profile_args(uninstall_parser, "Uninstall")
    uninstall_parser.set_defaults(func=uninstall)

    # Clean
    clean_parser = subparsers.add_parser("clean", help="Clean project targets", description="Clean one or more project targets. By default, cleans all targets for the default profiles.")
    clean_parser.add_argument("--nuke", help="The nuclear option. Removes the entire build directory, including all targets for all profiles, meaning that the project must be reconfigured before subsequent builds.", action="store_true")
    _add_profile_args(clean_parser, "Clean")
    clean_parser.set_defaults(func=clean)

    # Display help if no arguments are provided.
    if len(sys.argv) < 2:
        parser.print_help()

    args, unknown = parser.parse_known_args()
    # If there are unknown arguments, make the parser display an error.
    # Done this way because a parser option provided after a subparser will
    # result in an unknown arg that isn't really unknown.
    if unknown:
        parser.parse_args(unknown)
    # Dispatch
    if hasattr(args, "func"):
        args.func(args)
