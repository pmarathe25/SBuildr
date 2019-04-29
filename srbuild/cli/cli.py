from srbuild.generator.rbuild import RBuildGenerator
from srbuild.project.project import Project
from srbuild.logger import G_LOGGER

import argparse

# TODO: Docstrings
# Sets up the the command-line interface for the given project/generator combination.
def cli(project: Project, GeneratorType: type = RBuildGenerator):
    generator = GeneratorType(project)

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
        result = generator.build(targets)
        if result.returncode:
            import os, sys
            terminal_width, _ = os.get_terminal_size(0)
            G_LOGGER.critical(f"Build failed with:\n\n{' Captured stdout '.center(terminal_width, '=')}\n{result.stdout.decode(sys.stdout.encoding)}\n\n{' Captured stderr '.center(terminal_width, '=')}\n{result.stderr.decode(sys.stdout.encoding)}")

    def run(args):
        # TODO(2): Finish run implementation
        pass

    def install(args):
        # TODO(3): Finish install implementation
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
    run_parser = subparsers.add_parser("run", help="Run a project executable", description="Run a project executable")
    run_parser.set_defaults(func=run)
    # Install
    install_parser = subparsers.add_parser("install", help="Install a project target", description="Install a project target")
    install_parser.set_defaults(func=install)

    # Dispatch
    args, _ = parser.parse_known_args()
    if args.very_verbose:
        G_LOGGER.severity = G_LOGGER.VERBOSE
    elif args.verbose:
        G_LOGGER.severity = G_LOGGER.DEBUG


    if hasattr(args, "func"):
        args.func(args)
