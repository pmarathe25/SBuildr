from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.project.project import Project
from sbuildr.cli.cli import cli

from test_tools import PATHS, TESTS_ROOT, ROOT

import subprocess
import shutil
import sys
import os

INSTALL_DIR_ARGS = ["-I", PATHS["build"], "-L", PATHS["build"], "-X", PATHS["build"]]

def test_public_imports():
    import sbuildr
    from sbuildr import compiler, linker, BuildFlags, Project, Profile
    from sbuildr.backends import Backend, RBuildBackend

class TestIntegration(object):
    @classmethod
    def setup_class(cls):
        cls.teardown_class()
        print(f"Creating build directory: {PATHS['build']}")
        os.mkdir(PATHS["build"])

    @classmethod
    def teardown_class(cls):
        print(f"Removing build directory: {PATHS['build']}")
        shutil.rmtree(PATHS["build"], ignore_errors=True)

    def setup_method(self):
        self.proj = Project(root=ROOT)
        self.libmath = self.proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        self.test = self.proj.executable("test", sources=["test.cpp"], libs=["stdc++", self.libmath])
        [self.header] = self.proj.interfaces(["math.hpp"])

    def test_help_targets(self):
        sys.argv = ["", "help"]
        cli(self.proj)

    def test_can_build_project(self):
        # Build both targets for all profiles.
        targets = [self.libmath, self.test]
        self.proj.build(targets)

        # Ensure that the targets now exist
        for target in targets:
            for node in target.values():
                assert os.path.exists(node.path)

    def test_default_install_project(self):
        install_path = os.path.join(PATHS["build"], self.libmath["release"].name)
        # Install release profile
        sys.argv = ["", "install", "-f"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert os.path.exists(install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert not os.path.exists(install_path)

    # Installation when profile is specified
    def test_profile_install_project(self):
        install_path = os.path.join(PATHS["build"], self.libmath["debug"].name)
        release_install = os.path.join(PATHS["build"], self.libmath["release"].name)
        # Install
        sys.argv = ["", "install", "-f", "--debug"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert os.path.exists(install_path)
        assert not os.path.exists(release_install)
        # Then remove
        sys.argv = ["", "uninstall", "-f", "--debug"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert not os.path.exists(install_path)

    # Installation when target is specified
    def test_target_install_project(self):
        install_path = os.path.join(PATHS["build"], self.libmath["release"].name)
        test_install_path = os.path.join(PATHS["build"], self.test["release"].name)
        # Install
        sys.argv = ["", "install", "-f", "math"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert os.path.exists(install_path)
        assert not os.path.exists(test_install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f", "math"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert not os.path.exists(install_path)

    # Installation when no installation targets are specified.
    def test_empty_install(self):
        proj = Project(root=ROOT)
        proj.configure_backend()
        sys.argv = ["", "install", "-f"]
        cli(proj)

    def test_header_install(self):
        # Check that the return value is the correct path
        assert self.header == PATHS["math.hpp"]

        install_path = os.path.join(PATHS["build"], "math.hpp")
        # Install
        sys.argv = ["", "install", "-f"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert os.path.exists(install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f"] + INSTALL_DIR_ARGS
        cli(self.proj)
        assert not os.path.exists(install_path)
