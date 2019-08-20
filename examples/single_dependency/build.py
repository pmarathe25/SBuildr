#!/usr/bin/env python3
import sbuildr
import sbuildr.dependencies.builders as builders
import sbuildr.dependencies.fetchers as fetchers

import os
SCRIPT_DIR = os.path.dirname(__file__)
cppstdlib = sbuildr.Library("stdc++")

project = sbuildr.Project()

# Assumes that minimal_project is located in single_dependency/../minimal_project
# CopyFetcher does not support the version parameter, so we provide no version here.
# For other fetchers, the correct version should be provided.
minimal_project = sbuildr.dependencies.Dependency(fetchers.CopyFetcher(os.path.join(SCRIPT_DIR, os.pardir, "minimal_project")), builders.SBuildrBuilder(), version="")

# Add targets for this project
project.interfaces(["dep.hpp"])
libdep = project.library("dep", sources=["dep.cpp"], libs=[cppstdlib, minimal_project.library("math")])
project.test("test", sources=["test.cpp"], libs=[cppstdlib, libdep])
project.test("selfContainedTest", sources=["selfContainedTest.cpp"])

project.export()
