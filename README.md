# SBuildr - Stupid Buildr

A stupid, simple python-based meta-build system for C++ projects.

## Known Limitations
- SBuildr's header scanning functionality does not take into account preprocessor `#ifdef`s. This means that an `#include` in a `false` branch will still be used as a dependency during builds. Header scanning will also not work for paths containing escaped characters.
