# SBuildr Changelog
Dates are in YYYY-MM-DD format.

## v0.6.4 (2022-03-03)
- Updated CLI to inherit environment variables

## v0.6.3 (2022-03-03)
- Reduces logging output for builds.
- Changes `clean` behavior - will now always remove the common build directory, including artifacts for all profiles.
- Fixes a bug that would occur when `LD_LIBRARY_PATH` was not set.

## v0.6.2 (2020-01-10)
- `Dependency` will now create destination directories for fetchers if they do not exist.

## v0.6.1 (2019-09-07)
- Fixes a bug where tests were not being marked as `internal`.
- Fixes a bug where `configure` would not work if the specified targets had dependent targets that were not specified to `configure`.
- Fixes a bug where `configure` would configure all targets if an empty list of targets was provided.
- Fixes default list arguments in public API. Now, an empty list is distinguishable from a default argument.
- Fixes `FileManager`'s logic for disambiguating includes.
- Fixes `FileManager`'s logic for finding source nodes. This prevents headers from being scanned multiple times.
- Adds checks so that invalid target names are caught early.
- Adds default profiles to `sbuildr test`.
- Fixes a bug where multiple requests to a Dependency for the same library would result in only the last request being valid.
- Fixes a bug in `GitFetcher` when checking out different commits from different dependencies for the same source repository.

## v0.6.0 (2019-08-27)
- Adds `depends` argument to `Project.library()`, `Project.executable()`, `Project.test()`, and `Project.interfaces()`. This can be used to specify any dependencies not captured in the `libs` argument - for example, header-only packages.
- The `nuke` option in `Project.clean()` now removes all build directories rather than just the Project's build directory.
- Fixes a bug that prevented the `sbuildr` executable script from building test targets.
- Removes subcommands under `configure` in the `sbuildr` executable. Additionally, configure can now export a project using a specified build script.
- Changes `tests` back to `test` in the `sbuildr` executable.
- Adds Project API version so that old saved projects can be detected.
- Fetchers now support versioning. `GitFetcher` can checkout a specific commit, tag or branch.
- `Node`s now supply print commands to the backend, so that informative messages are shown during the build.
- Combines `Project`'s `find_dependencies`, `configure_graph` and `configure_backend` into `configure()`
- Hashes for build artifacts now take more variables into account, thereby preventing collisions.

## v0.5.0 (2019-08-21)
- `tests` in CLI now runs all profiles by default.
- `tests` now displays a summary at the end.
- Project's `install` has been modified to `interfaces` and now only accepts headers. Libraries and executables are now marked for installation by default, unless `internal=True` is specified.
- The `cli` install/uninstall functions now allow the user to specify paths for installing executables, libraries, and headers.
- Restructures so that `Generator` is now part of the `Project`.
- `targets` in `cli` has been renamed to `help`.
- Adds `configure` and `build` to the `Project`.
- Adds `DependencyBuilder`s and `DependencyFetcher`s for dependency management.
- Adds `GitFetcher` for retrieving source code from git repositories.
- Adds `CopyFetcher` for copying directories.
- Adds `SBuildrBuilder` for building projects using the SBuildr build system.
- Renames `Generator` and associated classes/files to `Backend`.
- Pulls in most functions from `cli` into `Project` to enable more powerful scripting.
- Adds `export()` function to `Project` that pickles and writes it into the specified path. `Project.load()` can be used to retrieve it.
- Removes lazy header scanning - file manager now scans source files as they are added.
- Profile build directories can now be outside of the project's build directory.
- All profiles now share a common build directory for intermediate objects. Final targets are still built in each profile's individual subdirectory.
- `Backend` now only accepts a single graph describing the whole project. Thus, the backend does not need to know about file manager, profiles, etc.
- Libraries are now linked in a portable way - instead of using paths, names are used.
- `Project` now display a command that can be used to reproduce any executables that are run via the API.
- `Project`'s `configure()` is now `configure_backend()`. Additionally, projects are no longer tied to backends.
- Adds `Library` class to better abstract external libraries. This also allows for better handling of nested loader search path dependencies.
- Removes `cli()` and adds `bin/sbuildr` in its place. `bin/sbuildr` operates on saved projects, so it is much faster than running the `build.py` script each time.
- `bin/sbuildr`'s `configure` is now `configure-backend`.
- Adds deferred library propagation. Profiles can now set up libraries just before the build.
- `Graph` `layers()` now only returns nodes that are actually in the graph.
- Moves `dependencies` directory up one level.
- Adds `find_dependencies` and `configure_graph` to `Project`
- Adds `single_dependency` example
- Adds library name propagation in addition to just `lib_dirs` previously
- `configure_graph()` is now able to construct partial graphs.
- `Project` API functions no longer automatically call each other.
- `SBuildrBuilder` now proapagates `sys.path` to the `PYTHONPATH` environment variable correctly.
- Adds versioning for `DependencyMetadata` so dependencies in the cache with old versions of Metadata will automatically be rebuilt.
- Adds support for multiple build artifacts from nodes. Only the final artifact is usable by other nodes.
- All targets are now created in the common build directory. The per-profile build directories have hard-links to the targets in the common directory for ease-of-use.

## v0.4.1 (2019-07-11)
- Changes generator to favor false positives (longer builds) for `needs_configure()` rather than false negatives (broken builds).
- Fixes a bug where a header with no project includes would be scanned multiple times during configuration.
- Adds support for defining macros via the compiler.

## v0.4.0 (2019-07-06)
- Changes `test` command to `tests`
- Adds suggestion to reconfigure project on build failure.
- The generator build command now accepts `Node` rather than `ProjectTarget`s.
- Greatly simplifies install/uninstall `cli` functions.

## v0.3.2 (2019-06-29)
- Adds prerequisites section to README

## v0.3.1 (2019-06-27)
- Adds `minimal_project` as an example in the `examples/` directory
- Adds Sphinx configuration files for doc generation.

## v0.3.0 (2019-06-26)
- Fixes an issue with duplicate libraries when linking.
- Adds documentation for public API functions.

## v0.2.3 (2019-05-04)
- Adds `test` to `cli()` and `Project` to provide a convenient test runner.

## v0.2.2 (2019-05-03)
- Fixes an issue with absolute paths in `#include`s not being handled correctly.

## v0.2.1 (2019-05-03)
- Fixes errors in `setup.py` that prevented files from being packaged.

## v0.2.0 (2019-05-03)
- Disables logging when python is run with -O. This can provide some speed improvements.
- Adds CompilerDef/LinkerDef to isolate behavior specific to individual compilers/linkers. Compiler/Linker can now operate in a platform-agnostic way.
- Adds BuildFlags to make compiler/linker flags platform agnostic from the user's perspective.
- Adds Graph and rbuild generator.
- Adds raw options to BuildFlags
- Adds `+` and `+=` overloads for BuildFlags
- Adds Project, which can track one or more directories and the files contained within.
- Adds FileManager, which can determine include directories required for a given file, assuming included files are also tracked by the manager.
- Adds the concept of `Profile`s, which allow for building the same targets with different options.
- Project now lazily evaluates targets, and only when `configure` is invoked.
- Adds `exclude_dirs` option to `FileManager`
- Split `FileManager`'s '`source_info` into `source`, which adds sources to the graph, and `scan` which scans for include directories. Removed `includes` since that information is now part of the `Node`.
- `FileManager` now tracks root directory and build directory instead of `Project` tracking it directly.
- Smarter `find` function in `FileManager`. Additionally, `source` uses `find` to make sure sources exist.
- Adds `external` to `FileManager` to be able to track files external to the project.
- `FileManager`'s `find` will now accept absolute paths that are outside the project.
- Improved handling of libraries in `Project`
- Overhauled `Generator` API
- `FileManager` can now create directories, but only in its build directory.
- `Generator` now accepts `ProjectTarget`s to build rather than `LinkedNode`s
- Adds basic implementation of `cli()` with `configure` and `build` and a basic usage example.
- Adds `run` implementation in `cli()` that operates on the default profile.
- Adds `rm` to `FileManager` so that it can remove paths located in the build directory.
- Adds the nuclear option to `clean` in `cli()`
- Verbosity is now set during import, so that pre-subparser logging messages are displayed correctly.
- RBuildBackend updated to work with rbuild 0.3.0.
- `cli()` now accepts profile options for subparsers.
- Adds `install` to `cli()`
- Adds `uninstall` and `help` to `cli()`
- Adds suffixes for profiles. These will be applied to files when they are installed.
- Targets now support per-profile install paths
- `install` now supports file paths in addition to `ProjectTarget`s

## v0.1.0 (2019-02-16)
- Initial version, basic compiler functionality.
