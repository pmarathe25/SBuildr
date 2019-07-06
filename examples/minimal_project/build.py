#!/usr/bin/env python
import sbuildr
import os

project = sbuildr.Project()

# Build a library using two source files. Note that headers do not have to be specified manually.
# Full file paths are only required in cases where a partial path would be ambiguous.
libmath = project.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])

# Set the installation location for the library created above to /usr/local/lib.
project.install(libmath, path=os.path.join("/", "usr", "local", "lib"))

# Set the installation location for the public header to /usr/local/include.
project.install("math.hpp", path=os.path.join("/", "usr", "local", "include"))

# Specify a test for the project using the test.cpp source file. The resulting executable will be linked
# against the library created above.
test = project.test("test", sources=["test.cpp"], libs=["stdc++", libmath])

# Enable this script to be used interactively on the command-line
sbuildr.cli(project)
