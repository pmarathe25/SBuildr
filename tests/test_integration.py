from srbuild.project.project import Project
from srbuild.generator.rbuild import RBuildGenerator

from test_tools import PATHS, TESTS_ROOT, ROOT

import subprocess
import shutil
import os

class TestIntegration(object):
    @classmethod
    def setup_class(cls):
        cls.teardown_class()
        print(f"Creating build directory: {PATHS['build']}")
        os.mkdir(PATHS["build"])

    @classmethod
    def teardown_class(cls):
        print(f"Removing build directory: {PATHS['build']}")
        try:
            shutil.rmtree(PATHS["build"])
        except FileNotFoundError:
            pass

    def test_can_build_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        test = proj.executable("test", sources=["test.cpp"], libs=["stdc++", libmath])
        # Generate config file
        generator = RBuildGenerator(proj)
        generator.generate()

        # Build both targets for all profiles.
        targets = [libmath, test]
        generator.build(targets)
        # Ensure that the targets now exist
        for target in targets:
            for _, node in target.items():
                assert os.path.exists(node.path)
