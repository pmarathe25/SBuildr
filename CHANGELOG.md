# SRBuild Changelog
Dates are in YYYY-MM-DD format.

## SRBuild vNext
- Renamed to SRBuild.
- Disables logging when python is run with -O. This can provide some speed improvements.
- Added CompilerDef/LinkerDef to isolate behavior specific to individual compilers/linkers. Compiler/Linker can now operate in a platform-agnostic way.
- Adds BuildFlags to make compiler/linker flags platform agnostic from the user's perspective.
- Simplifies CPP Nodes to 3 categories: Source, Compiled, and Linked.
- Adds Graph

## SRBuild v0.1.0 (2019-02-16)
- Initial version, basic compiler functionality.
