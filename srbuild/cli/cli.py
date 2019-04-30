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

# Set up the top-level parser. This needs to happen at import time so that logging verbosity is set early.
parser = argparse.ArgumentParser(description="Builds this project")
parser.add_argument("-v", "--verbose", help="Enable verbose logging output", action="store_true")
parser.add_argument("-vv", "--very-verbose", help="Enable very verbose logging output", action="store_true")

args, _ = parser.parse_known_args()
if args.very_verbose:
    G_LOGGER.verbosity = logger.Verbosity.VERBOSE
elif args.verbose:
    G_LOGGER.verbosity = logger.Verbosity.DEBUG

# TODO: Docstrings
# Sets up the the command-line interface for the given project/generator combination.
# When no profile(s) are specified, default_profile will be used.
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
        output = f"\n\n{' Captured stdout '.center(terminal_width, '=')}\n{result.stdout.decode(sys.stdout.encoding)}\n\n{' Captured stderr '.center(terminal_width, '=')}\n{result.stderr.decode(sys.stdout.encoding)}"
        if result.returncode:
            G_LOGGER.critical(f"Build failed with:{output}")
        return output

    # Given target names, returns the corresponding targets.
    def _select_targets(tgt_names: List[str]) -> List[ProjectTarget]:
        targets = []
        for tgt_name in args.target:
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

    def configure(args):
        G_LOGGER.info(f"Generating configuration files in build directory: {project.files.build_dir}")
        generator.generate()

    @needs_configure
    def build(args):
        # TODO(1): Build only for the profiles specified.
        # By default, build all targets
        targets = _select_targets(args.targets) or (list(project.libraries.values()) + list(project.executables.values()))
        G_LOGGER.info(f"Building targets: {[target.name + (' (lib)' if target.is_lib else ' (exe)') for target in targets]}")
        G_LOGGER.debug(f"Targets: {targets}")
        _check_returncode(generator.build(targets))

    @needs_configure
    def run(args):
        # TODO(2): Finish implementation
        # TODO: Run for the specified profile.
        if args.target not in project.executables:
            G_LOGGER.critical(f"Could not find target: {args.target} in project executables. Note: Available targets are: {list(project.executables.keys())}")
        target = project.executables[args.target]
        # Build for this profile. TODO: Replace this with correct profile.
        _check_returncode(generator.build([target], profiles=[default_profile]))
        G_LOGGER.log(_check_returncode(subprocess.run([target[default_profile].path], capture_output=True)))

    @needs_configure
    def install(args):
        # TODO(3): Finish implementation
        pass

    def clean(args):
        # TODO(3): Finish implementation, per-profile and per-target cleaning.
        # When supplied no arguments, this will remove the whole build directory for each profile.
        G_LOGGER.info("Cleaning...")
        to_remove = [prof.build_dir for prof in project.profiles.values()]
        # The nuclear option
        if args.nuke:
            to_remove = [project.build_dir]
        for path in to_remove:
            G_LOGGER.info(f"\tRemoving {path}")
            project.files.rm(path)

    # By setting defaults, each subparser automatically invokes a function to execute it's actions.
    subparsers = parser.add_subparsers()
    # Configure
    configure_parser = subparsers.add_parser("configure", help="Generate build configuration files", description="Generate a build configuration file for the project")
    configure_parser.set_defaults(func=configure)
    # Build
    build_parser = subparsers.add_parser("build", help="Build project targets", description="Build one or more project targets")
    build_parser.add_argument("targets", nargs='*', help="Targets to build. Builds all targets by default", default=[])
    build_parser.set_defaults(func=build)
    # Run
    # TODO: This should accept --profile as arguments. Add each to a mutually exclusive group.
    run_parser = subparsers.add_parser("run", help="Run a project executable", description="Run a project executable")
    run_parser.add_argument("target", help="Target corresponding to an executable")
    run_parser.set_defaults(func=run)
    # Install
    install_parser = subparsers.add_parser("install", help="Install a project target", description="Install a project target")
    install_parser.set_defaults(func=install)
    # Clean
    clean_parser = subparsers.add_parser("clean", help="Clean project targets", description="Clean one or more project targets. If no arguments are provided, cleans all targets.")
    clean_parser.add_argument("--nuke", help="The nuclear option. Removes the entire build directory, meaning that the project must be reconfigured before subsequent builds.")
    clean_parser.set_defaults(func=clean)

    # Dispatch
    args, unknown = parser.parse_known_args()
    if unknown:
        G_LOGGER.critical(f"Unknown arguments: {unknown}")

    if hasattr(args, "func"):
        args.func(args)
