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

    def write_rbuild_config(self, config: str) -> str:
        config_path = os.path.join(PATHS["build"], "rbuild")
        with open(config_path, "w") as f:
            f.write(config)
        return config_path

    def test_can_build_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        test = proj.executable("test", sources=["test.cpp"], libs=["stdc++", libmath])
        proj.configure()
        # TODO(0): Figure out where this should happen. Can't be during configure, as it needs to run
        # between cleans too (which may not clean the build files)
        for profile in proj.profiles.values():
            os.mkdir(profile.build_dir)
        # Generate config file
        generator = RBuildGenerator()
        config = generator.generate(proj)
        # Write to disk and then try to build.
        config_path = self.write_rbuild_config(config)
        targets = list(libmath.values()) + list(test.values())
        build_cmd = generator.build_command(config_path, targets)
        print(f"Running build command: {build_cmd}")
        subprocess.run(build_cmd)
        # Ensure that the targets now exist
        for target in targets:
            assert os.path.exists(target.path)
