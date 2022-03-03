# SBuildr - Stupid Buildr

A stupid, simple python-based meta-build system for C++ projects.

## Installation

### Prerequisites

1. [RBuild](https://github.com/pmarathe25/RBuild)
    - Install [Cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html)
    - Run `cargo install rbuild`

### Installing from PyPI
`pip install sbuildr`

### Installing from Source
1. Clone the SBuildr [source repository](https://github.com/pmarathe25/SBuildr).
2. Install locally with `python setup.py install`

## A Small Example

For this example, we will assume the following directory structure:
```
minimal_project
├── build.py
├── include
│   └── math.hpp
├── src
│   ├── factorial.cpp
│   ├── factorial.hpp
│   ├── fibonacci.cpp
│   ├── fibonacci.hpp
│   └── utils.hpp
└── tests
    └── test.cpp
```

The corresponding `build.py` file might look like this:

```python
#!/usr/bin/env python
import sbuildr
import os

project = sbuildr.Project()

# Build a library using two source files. Note that headers do not have to be specified manually.
# Full file paths are only required in cases where a partial path would be ambiguous.
libmath = project.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])

# Specify that math.hpp is part of the public API for this library.
project.interfaces(["math.hpp"])

# Specify a test for the project using the test.cpp source file. The resulting executable will
# be linked against the library created above.
test = project.test("test", sources=["test.cpp"], libs=["stdc++", libmath])

# Enable this script to be used interactively on the command-line
project.export()
```

The call to the `cli()` function allows us to use the script to build interactively in a shell.
For example, to run all tests registered for this project, you can run: `./build.py test`. This will configure the project, build all dependencies, and finally run tests.

To view all available commands, you can run `./build.py --help`

<!-- TODO: Explain profiles -->

## API Documentation
For more information, see the [API Documentation](https://sbuildr.readthedocs.io/en/stable/)

## Known Limitations
- SBuildr's header scanning functionality does not take into account preprocessor `#ifdef`s. This means that an `#include` in a `false` branch will still be used as a dependency during builds. Header scanning will also not work for paths containing escaped characters.
