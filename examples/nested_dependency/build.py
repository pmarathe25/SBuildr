#!/usr/bin/env python3
import sbuildr
from sbuildr.dependencies import builders, fetchers

import pathlib
import os

cppstdlib = sbuildr.Library("stdc++")
project = sbuildr.Project()

# Assumes that single_dependency is located in ~/Code/SBuildr/examples/single_dependency
single_dependency_path = os.path.abspath(
    os.path.join(pathlib.Path.home(), "Code", "SBuildr", "examples", "single_dependency")
)
single_dependency = sbuildr.dependencies.Dependency(
    fetchers.CopyFetcher(single_dependency_path), builders.SBuildrBuilder()
)

# Add targets for this project
project.interfaces(["doubleDep.hpp"])
lib_double_dep = project.library(
    "doubleDep", sources=["doubleDep.cpp"], libs=[cppstdlib, single_dependency.library("dep")]
)
project.test("test", sources=["test.cpp"], libs=[cppstdlib, lib_double_dep])
project.test("selfContainedTest", sources=["selfContainedTest.cpp"])

project.export()
