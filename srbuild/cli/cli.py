from srbuild.generator.rbuild import RBuildGenerator
from srbuild.project.project import Project
from srbuild.project.target import ProjectTarget
from srbuild.logger import G_LOGGER
import srbuild.logger as logger

from typing import List
import subprocess
import argparse
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

# TODO: Docstrings
# Sets up the the command-line interface for the given project/generator combination.
# When no profile(s) are specified, default_profile will be used.
# TODO: Make default profile a list, and [] should correspond to all profiles.
def cli(project: Project, GeneratorType: type=RBuildGenerator, default_profile="debug"):
    generator = GeneratorType(project)

    def needs_configure(func, *args, **kwargs):
        def wrapper(*args, **kwargs):
            if generator.needs_configure():
                G_LOGGER.critical(f"'{func.__name__}' requires the project to be configured, but project has either not been configured yet, or configuration is outdated. Please run `configure`.")
            return func(*args, **kwargs)
        return wrapper

    # Returns the captured output
    # TODO: Subprocess management needs to be centralized somewhere.
    def _check_returncode(result: subprocess.CompletedProcess) -> str:
        terminal_width, _ = os.get_terminal_size(0)
        output = f"\n{' Captured stdout '.center(terminal_width, '=')}\n{result.stdout.decode(sys.stdout.encoding)}\n{' Captured stderr '.center(terminal_width, '=')}\n{result.stderr.decode(sys.stdout.encoding)}"
        if result.returncode:
            G_LOGGER.critical(f"Build failed with:{output}")
        return output

    # Given target names, returns the corresponding targets.
    def _select_targets(tgt_names: List[str]) -> List[ProjectTarget]:
        targets = []
        for tgt_name in tgt_names:
            if tgt_name not in project:
                G_LOGGER.critical(f"Could not find tgt_name: {tgt_name} in project.")
            if tgt_name in project.libraries:
                G_LOGGER.verbose(f"Found library for tgt_name: {tgt_name}")
                targets.append(project.libraries[tgt_name])
            if tgt_name in project.executables:
                G_LOGGER.verbose(f"Found executable for tgt_name: {tgt_name}")
                targets.append(project.executables[tgt_name])
            if tgt_name in project.executables and tgt_name in project.libraries:
                G_LOGGER.warning(f"Target: {tgt_name} refers to both an executable and a library. Selecting both.")
        return targets

    # Given argparse's args struct, parses out profile flags, and returns a list of profile names included.
    def _select_profile_names(args) -> List[str]:
        return [prof_name for prof_name in project.profiles.keys() if getattr(args, prof_name)]

    def configure(args):
        G_LOGGER.info(f"Generating configuration files in build directory: {project.files.build_dir}")
        generator.generate()

    @needs_configure
    def build(args):
        # By default, build all targets for the default profile..
        targets = _select_targets(args.targets) or (list(project.libraries.values()) + list(project.executables.values()))
        prof_names = _select_profile_names(args) or [default_profile]
        G_LOGGER.info(f"Building targets: {[target.name + (' (lib)' if target.is_lib else ' (exe)') for target in targets]} for profiles: {prof_names}")
        G_LOGGER.debug(f"Targets: {targets}")
        _check_returncode(generator.build(targets, profiles=prof_names))

    @needs_configure
    def run(args):
        # TODO(2): Finish implementation
        # TODO: Run for the specified profile.
        if args.target not in project.executables:
            G_LOGGER.critical(f"Could not find target: {args.target} in project executables. Note: Available targets are: {list(project.executables.keys())}")
        target = project.executables[args.target]
        prof_name = default_profile
        prof_names = _select_profile_names(args)
        if prof_names:
            # Only one profile can be specified to run.
            assert len(prof_names) == 1
            prof_name = prof_names[0]
        _check_returncode(generator.build([target], profiles=[prof_name]))
        G_LOGGER.info(f"Running target: {args.target}, for profile: {prof_name}:\n{target[prof_name].path}")
        G_LOGGER.log(_check_returncode(subprocess.run([target[prof_name].path], capture_output=True)))

    @needs_configure
    def install(args):
        # TODO(1): Finish implementation
        pass

    def clean(args):
        # TODO(3): Finish implementation, add per-target cleaning.
        to_remove = []
        if args.nuke:
            # The nuclear option
            to_remove = [project.build_dir]
            G_LOGGER.info(f"Initiating Nuclear Protocol!")
        else:
            # By default, cleans all targets for the default profile.
            prof_names = _select_profile_names(args) or [default_profile]
            to_remove = [project.profiles[prof_name].build_dir for prof_name in prof_names]
            G_LOGGER.info(f"Cleaning targets for profiles: {prof_names}")
        # Remove
        for path in to_remove:
            G_LOGGER.info(f"\tRemoving {path}")
            project.files.rm(path)

    parser = argparse.ArgumentParser(description="Builds this project")
    parser.add_argument("-v", "--verbose", help="Enable verbose logging output", action="store_true")
    parser.add_argument("-vv", "--very-verbose", help="Enable very verbose logging output", action="store_true")

    # By setting defaults, each subparser automatically invokes a function to execute it's actions.
    subparsers = parser.add_subparsers()
    # Configure
    configure_parser = subparsers.add_parser("configure", help="Generate build configuration files", description="Generate a build configuration file for the project")
    configure_parser.set_defaults(func=configure)

    # Build
    build_parser = subparsers.add_parser("build", help="Build project targets", description="Build one or more project targets")
    build_parser.add_argument("targets", nargs='*', help="Targets to build. Builds all targets for the default profile by default", default=[])
    for prof_name in project.profiles.keys():
        build_parser.add_argument(f"--{prof_name}", help=f"Build targets using the {prof_name} profile", action="store_true")
    build_parser.set_defaults(func=build)

    # Run
    run_parser = subparsers.add_parser("run", help="Run a project executable", description="Run a project executable")
    run_parser.add_argument("target", help="Target corresponding to an executable")
    run_profile_group = run_parser.add_mutually_exclusive_group()
    for prof_name in project.profiles.keys():
        run_profile_group.add_argument(f"--{prof_name}", help=f"Run the {prof_name} profile's target", action="store_true")
    run_parser.set_defaults(func=run)

    # Install
    install_parser = subparsers.add_parser("install", help="Install a project target", description="Install a project target")
    install_parser.set_defaults(func=install)

    # Clean
    clean_parser = subparsers.add_parser("clean", help="Clean project targets", description="Clean one or more project targets. If no arguments are provided, cleans all targets for the default profile.")
    clean_parser.add_argument("--nuke", help="The nuclear option. Removes the entire build directory, including all targets for all profiles, meaning that the project must be reconfigured before subsequent builds.", action="store_true")
    for prof_name in project.profiles.keys():
        clean_parser.add_argument(f"--{prof_name}", help=f"Cleans targets of the {prof_name} profile", action="store_true")
    clean_parser.set_defaults(func=clean)

    # Dispatch
    args, unknown = parser.parse_known_args()
    # If there are unknown arguments, make the parser display an error.
    # Done this way because a parser option provided after a subparser will
    # result in an unknown arg that isn't really unknown.
    if unknown:
        parser.parse_args(unknown)

    if hasattr(args, "func"):
        args.func(args)
