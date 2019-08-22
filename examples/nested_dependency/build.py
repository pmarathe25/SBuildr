#!/usr/bin/env python3
import sbuildr
import sbuildr.dependencies.builders as builders
import sbuildr.dependencies.fetchers as fetchers

import pathlib
import os

cppstdlib = sbuildr.Library("stdc++")
project = sbuildr.Project()

# Assumes that single_dependency is located in nested_dependency/../single_dependency
# CopyFetcher does not support the version parameter, so we provide no version here.
# For other fetchers, the correct version should be provided.
single_dependency_path = os.path.abspath(os.path.join(pathlib.Path.home(), "Python", "SBuildr", "examples", "single_dependency"))
single_dependency = sbuildr.dependencies.Dependency(fetchers.CopyFetcher(single_dependency_path), builders.SBuildrBuilder(), version="")

# Add targets for this project
project.interfaces(["doubleDep.hpp"])
lib_double_dep = project.library("doubleDep", sources=["doubleDep.cpp"], libs=[cppstdlib, single_dependency.library("dep")])
project.test("test", sources=["test.cpp"], libs=[cppstdlib, lib_double_dep])
project.test("selfContainedTest", sources=["selfContainedTest.cpp"])

project.export()
