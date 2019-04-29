from srbuild.generator.rbuild import RBuildGenerator
from srbuild.project.project import Project
from srbuild.logger import G_LOGGER
import srbuild.logger as logger

import subprocess
import argparse
import sys
import os

# TODO: Docstrings
# Sets up the the command-line interface for the given project/generator combination.
# When no profile(s) are specified, default_profile will be used.
def cli(project: Project, GeneratorType: type=RBuildGenerator, default_profile="debug"):
    generator = GeneratorType(project)

    # Returns the captured output
    # TODO: Subprocess management needs to be centralized somewhere.
    def check_returncode(result: subprocess.CompletedProcess) -> str:
        terminal_width, _ = os.get_terminal_size(0)
        output = f"\n\n{' Captured stdout '.center(terminal_width, '=')}\n{result.stdout.decode(sys.stdout.encoding)}\n\n{' Captured stderr '.center(terminal_width, '=')}\n{result.stderr.decode(sys.stdout.encoding)}"
        if result.returncode:
            G_LOGGER.critical(f"Build failed with:{output}")
        return output


    def configure(args):
        G_LOGGER.info(f"Generating configuration files in build directory: {project.files.build_dir}")
        generator.generate()

    def build(args):
        # TODO(1): Build only for the profiles specified.
        targets = []
        for target in args.target:
            if target not in project:
                G_LOGGER.critical(f"Could not find target: {target} in project.")
            if target in project.libraries:
                G_LOGGER.verbose(f"Found library for target: {targt.name}")
                targets.append(project.libraries[target])
            if target in project.executables:
                G_LOGGER.verbose(f"Found executable for target: {targt.name}")
                targets.append(project.executables[target])
            if target in project.executables and target in project.libraries:
                G_LOGGER.warning(f"Target: {target} refers to both an executable and a library. Building both.")
        # By default, build all targets
        targets = targets or (list(project.libraries.values()) + list(project.executables.values()))
        G_LOGGER.info(f"Building targets: {[target.name for target in targets]}")
        G_LOGGER.debug(f"Targets: {targets}")
        check_returncode(generator.build(targets))

    def run(args):
        # TODO(2): Finish implementation
        # TODO: Run for the specified profile.
        if args.target not in project.executables:
            G_LOGGER.critical(f"Could not find target: {args.target} in project executables. Note: Available targets are: {list(project.executables.keys())}")
        target = project.executables[args.target]
        # Build for this profile. TODO: Replace this with correct profile.
        check_returncode(generator.build([target], profiles=[default_profile]))
        G_LOGGER.log(check_returncode(subprocess.run([target[default_profile].path], capture_output=True)))

    def install(args):
        # TODO(3): Finish implementation
        pass

    def clean(args):
        # TODO(3): Finish implementation
        pass

    # Set up argument parsers.
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
    build_parser.add_argument("target", nargs='*', help="Targets to build Builds all targets by default", default=[])
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
    clean_parser = subparsers.add_parser("clean", help="Clean project targets", description="Clean one or more project targets")
    clean_parser.set_defaults(func=clean)

    # Dispatch
    args, _ = parser.parse_known_args()
    if args.very_verbose:
        G_LOGGER.verbosity = logger.Verbosity.VERBOSE
    elif args.verbose:
        G_LOGGER.verbosity = logger.Verbosity.DEBUG


    if hasattr(args, "func"):
        args.func(args)
