from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.project.project import Project
from sbuildr.graph.node import Library

from test_tools import PATHS, TESTS_ROOT, ROOT

import subprocess
import tempfile
import shutil
import sys
import os

INSTALL_DIR_ARGS = ["-I", PATHS["build"], "-L", PATHS["build"], "-X", PATHS["build"]]
SBUILDR_ROOT = os.path.abspath(os.path.join(TESTS_ROOT, os.pardir))
SBUILDR_EXEC = os.path.join(SBUILDR_ROOT, "bin", "sbuildr")

def test_public_imports():
    import sbuildr
    from sbuildr import compiler, linker, BuildFlags, Project, Profile, Library
    from sbuildr.backends import Backend, RBuildBackend
    from sbuildr.dependencies import DependencyBuilder, DependencyFetcher, Dependency, DependencyLibrary
    from sbuildr.dependencies.builders import SBuildrBuilder
    from sbuildr.dependencies.fetchers import CopyFetcher, GitFetcher

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
        self.libmath = self.proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=[Library("stdc++")])
        self.test = self.proj.executable("test", sources=["test.cpp"], libs=[Library("stdc++"), self.libmath])
        [self.header] = self.proj.interfaces(["math.hpp"])
        self.saved_project = tempfile.NamedTemporaryFile()
        self.proj.fetch_dependencies()
        self.proj.configure_graph()
        self.proj.configure_backend()
        self.proj.export(self.saved_project.name)

    def test_help_targets(self):
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "help"])

    def test_can_build_project(self):
        # Build both targets for all profiles.
        targets = [self.libmath, self.test]
        self.proj.build(targets)

        # Ensure that the targets now exist
        for target in targets:
            for node in target.values():
                assert os.path.exists(node.path)

    def test_default_install_project(self):
        install_path = os.path.join(PATHS["build"], self.libmath["release"].basename)
        # Install release profile
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f"] + INSTALL_DIR_ARGS)
        assert os.path.exists(install_path)
        # Then remove
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f"] + INSTALL_DIR_ARGS)
        assert not os.path.exists(install_path)

    # Installation when profile is specified
    def test_profile_install_project(self):
        install_path = os.path.join(PATHS["build"], self.libmath["debug"].basename)
        release_install = os.path.join(PATHS["build"], self.libmath["release"].basename)
        # Install
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f", "--debug"] + INSTALL_DIR_ARGS)
        assert os.path.exists(install_path)
        assert not os.path.exists(release_install)
        # Then remove
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f", "--debug"] + INSTALL_DIR_ARGS)
        assert not os.path.exists(install_path)

    # Installation when target is specified
    def test_target_install_project(self):
        install_path = os.path.join(PATHS["build"], self.libmath["release"].basename)
        test_install_path = os.path.join(PATHS["build"], self.test["release"].basename)
        # Install
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f", "math"] + INSTALL_DIR_ARGS)
        assert os.path.exists(install_path)
        assert not os.path.exists(test_install_path)
        # Then remove
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f", "math"] + INSTALL_DIR_ARGS)
        assert not os.path.exists(install_path)

    # Installation when no installation targets are specified.
    def test_empty_install(self):
        proj = Project(root=ROOT)
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f"])

    def test_header_install(self):
        # Check that the return value is the correct path
        assert self.header == PATHS["math.hpp"]

        install_path = os.path.join(PATHS["build"], "math.hpp")
        # Install
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f"] + INSTALL_DIR_ARGS)
        assert os.path.exists(install_path)
        # Then remove
        subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f"] + INSTALL_DIR_ARGS)
        assert not os.path.exists(install_path)
