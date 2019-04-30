# SRBuild Changelog
Dates are in YYYY-MM-DD format.

## SRBuild vNext
- Renamed to SRBuild.
- Disables logging when python is run with -O. This can provide some speed improvements.
- Added CompilerDef/LinkerDef to isolate behavior specific to individual compilers/linkers. Compiler/Linker can now operate in a platform-agnostic way.
- Added BuildFlags to make compiler/linker flags platform agnostic from the user's perspective.
- Added Graph and rbuild generator.
- Added raw options to BuildFlags
- Added `+` and `+=` overloads for BuildFlags
- Added Project, which can track one or more directories and the files contained within.
- Added FileManager, which can determine include directories required for a given file, assuming included files are also tracked by the manager.
- Added the concept of `Profile`s, which allow for building the same targets with different options.
- Project now lazily evaluates targets, and only when `configure` is invoked.
- Added `exclude_dirs` option to `FileManager`
- Split `FileManager`'s '`source_info` into `source`, which adds sources to the graph, and `scan` which scans for include directories. Removed `includes` since that information is now part of the `Node`.
- `FileManager` now tracks root directory and build directory instead of `Project` tracking it directly.
- Smarter `find` function in `FileManager`. Additionally, `source` uses `find` to make sure sources exist.
- Added `external` to `FileManager` to be able to track files external to the project.
- `FileManager`'s `find` will now accept absolute paths that are outside the project.
- `Profile` now has runnable `target` function (untested).
- Improved handling of libraries in `Project`
- Implemented `Project.configure` and added `configured` attribute to `Project` to indicate whether the project is ready to build.
- Overhauled `Generator` API so it now takes a `configure`d `Project` as an input
- `FileManager` can now create directories, but only in its build directory.
- `Generator` now accepts `ProjectTarget`s to build rather than `LinkedNode`s
- Added basic implementation of `cli()` with `configure` and `build` and a basic usage example.
- Added `run` implementation in `cli()` that operates on the default profile.
- Added `rm` to `FileManager` so that it can remove paths located in the build directory.
- Added the nuclear option to `clean` in `cli()`
- Verbosity is now set during import, so that pre-subparser logging messages are displayed correctly.
- RBuildGenerator updated to work with rbuild 0.3.0.
- `cli()` now accepts profile options for subparsers.

## SRBuild v0.1.0 (2019-02-16)
- Initial version, basic compiler functionality.
