#!/usr/bin/env python
# For testing purposes only:
import os
import sys
CURDIR = os.path.dirname(__file__)
SRBUILD_DIR = os.path.abspath(os.path.join(CURDIR, os.pardir, os.pardir))
sys.path.insert(0, SRBUILD_DIR)

# Normal build files would start here:
import srbuild

# srbuild.logger.G_LOGGER.severity = srbuild.logger.G_LOGGER.VERBOSE

project = srbuild.Project()
libmath = project.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
test = project.executable("test", sources=["test.cpp"], libs=["stdc++", libmath])

srbuild.cli(project)
