#!/usr/bin/env python
# For testing purposes only:
import os
import sys
CURDIR = os.path.dirname(__file__)
SRBUILD_DIR = os.path.abspath(os.path.join(CURDIR, os.pardir, os.pardir))
sys.path.insert(0, SRBUILD_DIR)

# Normal build files would start here:
import srbuild

project = srbuild.Project()
libmath = project.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
libtest = project.library("test", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
install_dir = os.path.join(CURDIR, "build")
project.install(libtest, dir=install_dir)
project.install("utils.hpp", dir=install_dir)
test = project.executable("test", sources=["test.cpp"], libs=["stdc++", libtest])

srbuild.cli(project)
