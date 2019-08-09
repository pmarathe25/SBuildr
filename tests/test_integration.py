from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.project.project import Project
from sbuildr.cli.cli import cli

from test_tools import PATHS, TESTS_ROOT, ROOT

import subprocess
import shutil
import sys
import os

INSTALL_DIR_ARGS = ["-I", PATHS["build"], "-L", PATHS["build"], "-X", PATHS["build"]]

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

    def test_help_targets(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        test = proj.executable("test", sources=["test.cpp"], libs=["stdc++", libmath])

        sys.argv = ["", "help"]
        cli(proj)

    def test_can_build_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        test = proj.executable("test", sources=["test.cpp"], libs=["stdc++", libmath])
        # Generate config file
        proj.configure()

        # Build both targets for all profiles.
        targets = [libmath, test]
        proj.build(targets)

        # Ensure that the targets now exist
        for target in targets:
            for node in target.values():
                assert os.path.exists(node.path)

    def test_default_install_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        install_path = os.path.join(PATHS["build"], libmath["release"].name)
        # Install release profile
        sys.argv = ["", "install", "-f"] + INSTALL_DIR_ARGS
        cli(proj)
        assert os.path.exists(install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f"] + INSTALL_DIR_ARGS
        cli(proj)
        assert not os.path.exists(install_path)

    # Installation when profile is specified
    def test_profile_install_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        install_path = os.path.join(PATHS["build"], libmath["debug"].name)
        release_install = os.path.join(PATHS["build"], libmath["release"].name)
        # Install
        sys.argv = ["", "install", "-f", "--debug"] + INSTALL_DIR_ARGS
        cli(proj)
        assert os.path.exists(install_path)
        assert not os.path.exists(release_install)
        # Then remove
        sys.argv = ["", "uninstall", "-f", "--debug"] + INSTALL_DIR_ARGS
        cli(proj)
        assert not os.path.exists(install_path)

    # Installation when target is specified
    def test_target_install_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        test = proj.executable("test", sources=["test.cpp"], libs=["stdc++", libmath])
        install_path = os.path.join(PATHS["build"], libmath["release"].name)
        test_install_path = os.path.join(PATHS["build"], test["release"].name)
        # Install
        sys.argv = ["", "install", "-f", "math"] + INSTALL_DIR_ARGS
        cli(proj)
        assert os.path.exists(install_path)
        assert not os.path.exists(test_install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f", "math"] + INSTALL_DIR_ARGS
        cli(proj)
        assert not os.path.exists(install_path)

    # Installation when no installation targets are specified.
    def test_empty_install(self):
        proj = Project(root=ROOT)

        sys.argv = ["", "install", "-f"]
        cli(proj)

    def test_header_install(self):
        proj = Project(root=ROOT)
        [header] = proj.interfaces(["math.hpp"])
        # Check that the return value is the correct path
        assert header == PATHS["math.hpp"]

        install_path = os.path.join(PATHS["build"], "math.hpp")
        # Install
        sys.argv = ["", "install", "-f"] + INSTALL_DIR_ARGS
        cli(proj)
        assert os.path.exists(install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f"] + INSTALL_DIR_ARGS
        cli(proj)
        assert not os.path.exists(install_path)

    def test_public_imports(self):
        import sbuildr
        from sbuildr import compiler, linker, BuildFlags, Project, Profile
        from sbuildr.backends import Backend, RBuildBackend
