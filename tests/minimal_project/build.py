#!/usr/bin/env python
# For testing purposes only:
import os
import sys
CURDIR = os.path.dirname(__file__)
SBUILDR_DIR = os.path.abspath(os.path.join(CURDIR, os.pardir, os.pardir))
sys.path.insert(0, SBUILDR_DIR)

# Normal build files would start here:
import sbuildr

project = sbuildr.Project()
libmath = project.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
libtest = project.library("test", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
install_dir = os.path.join(CURDIR, "build")
project.install(libtest, dir=install_dir)
project.install("utils.hpp", dir=install_dir)
test = project.test("test", sources=["test.cpp"], libs=["stdc++", libtest])
test = project.executable("test_e", sources=["test.cpp"], libs=["stdc++", libtest])

sbuildr.cli(project)
