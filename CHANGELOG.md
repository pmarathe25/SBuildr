# SRBuild Changelog
Dates are in YYYY-MM-DD format.

## SRBuild vNext
- Renamed to SRBuild.
- Disables logging when python is run with -O. This can provide some speed improvements.
- Added CompilerDef/LinkerDef to isolate behavior specific to individual compilers/linkers. Compiler/Linker can now operate in a platform-agnostic way.
- Adds BuildFlags to make compiler/linker flags platform agnostic from the user's perspective.
- Adds Graph and rbuild generator.
- Adds raw options to BuildFlags
- Adds `+` and `+=` overloads for BuildFlags
- Removes all node categories except `Node`, which now only keeps track of arbitrary paths and associated commands
- Adds Project, which can track one or more directories and the files contained within.
- Adds FileManager, which can determine include directories required for a given file, assuming included files are also tracked by the manager.
- Adds the concept of `Profile`s, which allow for building the same targets with different options. 

## SRBuild v0.1.0 (2019-02-16)
- Initial version, basic compiler functionality.
