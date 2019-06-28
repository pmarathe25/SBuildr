from sbuildr.generator.rbuild import RBuildGenerator
from sbuildr.project.project import Project
from sbuildr.project.target import ProjectTarget
from sbuildr.logger import G_LOGGER
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
            G_LOGGER.critical(f"Failed with:\n{output}")
        return output

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
        return targets or (list(project.libraries.values()) + list(project.executables.values()))

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
        return [prof_name for prof_name in project.profiles.keys() if getattr(args, prof_name)] or default_profiles

    def _build_targets(targets: List[ProjectTarget], prof_names: List[str]):
        G_LOGGER.info(f"Building targets: {[target.name for target in targets]} for profiles: {prof_names}")
        G_LOGGER.debug(f"Targets: {targets}")
        _check_returncode(generator.build(targets, profiles=prof_names))

    def help_targets(args):
        targets = _select_targets(args)
        G_LOGGER.info(f"\n{_wrap_str(' Targets ')}")
        for target in targets:
            G_LOGGER.info(f"Target: {target}. Available Profiles:")
            for prof, node in target.items():
                G_LOGGER.info(f"\tProfile: {prof}. Path: {node.path}.")
                if node.install_path:
                    G_LOGGER.info(f"\t\tInstalls to: {node.install_path}")
        G_LOGGER.info(f"\n{_wrap_str(' Paths ')}")
        for path, install_path in project.installs.items():
            G_LOGGER.info(f"Path: {path}")
            G_LOGGER.info(f"\t\tInstalls to: {install_path}")

    def configure(args):
        generator.generate()

    @needs_configure
    def build(args) -> Tuple[List[ProjectTarget], List[str]]:
        targets = _select_targets(args)
        prof_names = _select_profile_names(args)
        _build_targets(targets, prof_names)

    @needs_configure
    def run(args):
        if args.target not in project.executables:
            G_LOGGER.critical(f"Could not find target: {args.target} in project executables. Note: Available targets are: {list(project.executables.keys())}")
        target = project.executables[args.target]
        prof_name = _select_profile_names(args)[0]
        _build_targets([target], [prof_name])
        G_LOGGER.log(f"\nRunning target: {target}, for profile: {prof_name}: {target[prof_name].path}", color=logger.Color.GREEN)
        G_LOGGER.log(_check_returncode(subprocess.run([target[prof_name].path], capture_output=True)))

    @needs_configure
    def test(args):
        tests = _select_test_targets(args)
        prof_names = _select_profile_names(args)
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

    # Copies src to dst
    def _copy_file(src, dst) -> bool:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            return True
        except PermissionError:
            G_LOGGER.error(f"Could not write to {dst}. Do you have sufficient privileges?")
            return False

    def _prune_install_targets(args):
        install_files, targets = [], []
        for tgt in args.targets:
            if tgt in project:
                targets.append(tgt)
            else:
                install_files.append(tgt)
        args.targets = targets
        install_files = install_files or list(project.installs.keys())
        return install_files, _select_targets(args)

    @needs_configure
    def install(args):
        # Filter out the non-targets (i.e. files), and select all targets by default.
        install_files, targets = _prune_install_targets(args)
        prof_names = _select_profile_names(args)
        _build_targets(targets, prof_names)
        for target in targets:
            for prof_name in prof_names:
                if prof_name in target:
                    install_path = target[prof_name].install_path
                    if install_path:
                        if _copy_file(target[prof_name].path, install_path):
                            G_LOGGER.info(f"Installed target: {target}, for profile: {prof_name} to {install_path}")
                    else:
                        G_LOGGER.warning(f"No installation path is specified for target: {target} for profile: {prof_name}")
                else:
                    G_LOGGER.warning(f"Target: {target} does not exist for profile: {prof_name}, will not install.")

        for install_file in install_files:
            if not install_file in project.installs:
                G_LOGGER.critical(f"{install_file} is neither a ProjectTarget, nor a registered path. Note: Registered paths: {list(project.installs.keys())}")
            if not os.path.exists(install_file):
                G_LOGGER.critical(f"Installation target: {install_file} was registered, but the path does not exist.")
            if _copy_file(install_file, project.installs[install_file]):
                G_LOGGER.info(f"Installed path: {install_file} to {project.installs[install_file]}")

    def uninstall(args):
        install_files, targets = _prune_install_targets(args)
        prof_names = _select_profile_names(args)
        if not args.force:
            G_LOGGER.warning(f"Uninstall dry-run, will not remove files without -f/--force.")
        for target in targets:
            for prof_name in prof_names:
                if prof_name in target:
                    install_path = target[prof_name].install_path
                    if install_path and os.path.exists(install_path):
                        if args.force:
                            G_LOGGER.info(f"Removing {install_path}")
                            os.remove(install_path)
                        else:
                            G_LOGGER.info(f"Would remove: {install_path}")
                else:
                    G_LOGGER.warning(f"Target: {target} does not exist for profile: {prof_name}, will not uninstall.")

        for install_file in install_files:
            if install_file not in project.installs:
                G_LOGGER.critical(f"{install_file} is neither a ProjectTarget, nor a registered path. Note: Registered paths: {list(project.installs.keys())}")
            path = project.installs[install_file]
            if os.path.exists(path):
                if args.force:
                    G_LOGGER.info(f"Removing {path}")
                    os.remove(path)
                else:
                    G_LOGGER.info(f"Would remove: {path}")

    def clean(args):
        # TODO(3): Finish implementation, add per-target cleaning.
        to_remove = []
        if args.nuke:
            # The nuclear option
            to_remove = [project.build_dir]
            G_LOGGER.info(f"Initiating Nuclear Protocol!")
        else:
            # By default, cleans all targets for the default profile.
            prof_names = _select_profile_names(args)
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
    test_parser = subparsers.add_parser("test", help="Run project tests", description="Run one or more project tests")
    test_parser.add_argument("targets", nargs='*', help="Targets to test. By default, tests all targets for the default profiles.", default=[])
    _add_profile_args(test_parser, "Test")
    test_parser.set_defaults(func=test)

    # Install
    install_parser = subparsers.add_parser("install", help="Install project targets", description="Install one or more project targets")
    install_parser.add_argument("targets", nargs='*', help="Targets to install. By default, installs all paths and targets for the default profiles.", default=[])
    _add_profile_args(install_parser, "Install")
    install_parser.set_defaults(func=install)

    # Uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall project targets", description="Uninstall one or more project targets")
    uninstall_parser.add_argument("-f", "--force", help="Remove targets. Without this flag, uninstall will only do a dry-run", action="store_true")
    uninstall_parser.add_argument("targets", nargs='*', help="Targets to uninstall. By default, uninstalls all paths and targets for the default profiles.", default=[])
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
