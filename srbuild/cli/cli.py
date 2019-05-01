from srbuild.generator.rbuild import RBuildGenerator
from srbuild.project.project import Project
from srbuild.project.target import ProjectTarget
from srbuild.logger import G_LOGGER
import srbuild.logger as logger

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
            G_LOGGER.critical(f"Failed with:{output}")
        return output

    # Given target names, returns the corresponding targets.
    # Falls back to returning all targets.
    def _select_targets(args) -> List[ProjectTarget]:
        targets = []
        for tgt_name in args.targets:
            if tgt_name not in project:
                G_LOGGER.critical(f"Could not find target: {tgt_name} in project.")
            if tgt_name in project.libraries:
                G_LOGGER.verbose(f"Found library for target: {tgt_name}")
                targets.append(project.libraries[tgt_name])
            if tgt_name in project.executables:
                G_LOGGER.verbose(f"Found executable for target: {tgt_name}")
                targets.append(project.executables[tgt_name])
            if tgt_name in project.executables and tgt_name in project.libraries:
                G_LOGGER.warning(f"Target: {tgt_name} refers to both an executable and a library. Selecting both.")
        return targets or (list(project.libraries.values()) + list(project.executables.values()))

    # Given argparse's args struct, parses out profile flags, and returns a list of profile names included.
    # Falls back to returning the default profile.
    def _select_profile_names(args) -> List[str]:
        return [prof_name for prof_name in project.profiles.keys() if getattr(args, prof_name)] or [default_profile]

    def _build_targets(targets: List[ProjectTarget], prof_names: List[str]):
        G_LOGGER.info(f"Building targets: {[target.name for target in targets]} for profiles: {prof_names}")
        G_LOGGER.debug(f"Targets: {targets}")
        _check_returncode(generator.build(targets, profiles=prof_names))

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
        [prof_name] = _select_profile_names(args)
        _build_targets([target], [prof_name])
        G_LOGGER.info(f"Running target: {targets.name}, for profile: {prof_names}:\n{targets[prof_names].path}")
        G_LOGGER.log(_check_returncode(subprocess.run([targets[prof_names].path], capture_output=True)))

    # TODO: FIXME: This will not work if user does not have permission to write to path
    @needs_configure
    def install(args):
        # Select all registered installation targets by default.
        registered_targets = [target for target in (list(project.executables.values()) + list(project.libraries.values())) if target.install_dir]
        targets = _select_targets(args) if args.targets else registered_targets
        [prof_name] = _select_profile_names(args)
        _build_targets(targets, [prof_name])
        for target in targets:
            # Create the required directory, then install
            if not target.install_dir:
                G_LOGGER.critical(f"Could not find an installation entry for target: {target.name}. Have you specified one with project.install()? Note: Installation entries: {registered_targets}")
            os.makedirs(target.install_dir, exist_ok=True)
            path = os.path.join(target.install_dir, target[prof_name].name)
            G_LOGGER.info(f"Installing target: {target.name}, for profile: {prof_name} to {path}")
            shutil.copyfile(target[prof_name].path, path)

    # TODO: Uninstall
    def uninstall(args):
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
            prof_names = _select_profile_names(args)
            to_remove = [project.profiles[prof_name].build_dir for prof_name in prof_names]
            G_LOGGER.info(f"Cleaning targets for profiles: {prof_names}")
        # Remove
        for path in to_remove:
            G_LOGGER.info(f"\tRemoving {path}")
            project.files.rm(path)

    parser = argparse.ArgumentParser(description="Builds this project")
    parser.add_argument("-v", "--verbose", help="Enable verbose logging output", action="store_true")
    parser.add_argument("-vv", "--very-verbose", help="Enable very verbose logging output", action="store_true")

    def _add_profile_args(parser_like, verb: str):
        for prof_name in project.profiles.keys():
            parser_like.add_argument(f"--{prof_name}", help=f"{verb} targets using the {prof_name} profile", action="store_true")

    # By setting defaults, each subparser automatically invokes a function to execute it's actions.
    subparsers = parser.add_subparsers()
    # Configure
    configure_parser = subparsers.add_parser("configure", help="Generate build configuration files", description="Generate a build configuration file for the project")
    configure_parser.set_defaults(func=configure)

    # Build
    build_parser = subparsers.add_parser("build", help="Build project targets", description="Build one or more project targets")
    build_parser.add_argument("targets", nargs='*', help="Targets to build. By default, builds all targets for the default profile.", default=[])
    _add_profile_args(build_parser, "Build")
    build_parser.set_defaults(func=build)

    # Run
    run_parser = subparsers.add_parser("run", help="Run a project executable", description="Run a project executable")
    run_parser.add_argument("target", help="Target corresponding to an executable")
    run_profile_group = run_parser.add_mutually_exclusive_group()
    _add_profile_args(run_profile_group, "Run")
    run_parser.set_defaults(func=run)

    # Install
    install_parser = subparsers.add_parser("install", help="Install project targets", description="Install one or more project targets")
    install_parser.add_argument("targets", nargs='*', help="Targets to install. By default, installs all targets for the default profile.", default=[])
    install_parser.set_defaults(func=install)
    install_profile_group = install_parser.add_mutually_exclusive_group()
    _add_profile_args(install_profile_group, "Install")

    # Clean
    clean_parser = subparsers.add_parser("clean", help="Clean project targets", description="Clean one or more project targets. By default, cleans all targets for the default profile.")
    clean_parser.add_argument("--nuke", help="The nuclear option. Removes the entire build directory, including all targets for all profiles, meaning that the project must be reconfigured before subsequent builds.", action="store_true")
    _add_profile_args(clean_parser, "Clean")
    clean_parser.set_defaults(func=clean)

    args, unknown = parser.parse_known_args()
    # If there are unknown arguments, make the parser display an error.
    # Done this way because a parser option provided after a subparser will
    # result in an unknown arg that isn't really unknown.
    if unknown:
        parser.parse_args(unknown)
    # Dispatch
    if hasattr(args, "func"):
        args.func(args)
