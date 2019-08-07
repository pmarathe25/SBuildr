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

sbuildr.cli(project)
