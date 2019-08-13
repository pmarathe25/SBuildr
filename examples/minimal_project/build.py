#!/usr/bin/env python3
# DEBUG:
import sys
print(sys.path)

import sbuildr
cppstdlib = sbuildr.Library("stdc++")

project = sbuildr.Project()

# Build a library using two source files. Note that headers do not have to be specified manually.
# Full file paths are only required in cases where a partial path would be ambiguous.
libmath = project.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=[cppstdlib])

# Specify that math.hpp is part of the public API for this library.
project.interfaces(["math.hpp"])

# Specify a test for the project using the test.cpp source file. The resulting executable will
# be linked against the library created above.
test = project.test("test", sources=["test.cpp"], libs=[cppstdlib, libmath])

# Save the project for use with the sbuildr command line utility.
project.export()
