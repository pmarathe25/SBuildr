from sbuildr.generator.rbuild import RBuildGenerator
from sbuildr.project.project import Project
from sbuildr.cli.cli import cli

from test_tools import PATHS, TESTS_ROOT, ROOT

import subprocess
import shutil
import sys
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
        nodes = []
        for target in targets:
            nodes.extend(target.values())

        generator.build(nodes)

        # Ensure that the targets now exist
        for target in targets:
            for node in target.values():
                assert os.path.exists(node.path)

    def test_default_install_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        install_path = proj.install(libmath, PATHS["build"])
        # Install
        sys.argv = ["", "install"]
        cli(proj)
        assert os.path.exists(install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f"]
        cli(proj)
        assert not os.path.exists(install_path)

    # Installation when profile is specified
    def test_profile_install_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        release_install = proj.install(libmath, PATHS["build"])
        install_path = proj.install(libmath, PATHS["build"], profile="debug")
        # Install
        sys.argv = ["", "install", "--debug"]
        cli(proj)
        assert os.path.exists(install_path)
        assert not os.path.exists(release_install)
        # Then remove
        sys.argv = ["", "uninstall", "-f", "--debug"]
        cli(proj)
        assert not os.path.exists(install_path)

    # Installation when target is specified
    def test_target_install_project(self):
        proj = Project(root=ROOT)
        libmath = proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        test = proj.executable("test", sources=["test.cpp"], libs=["stdc++", libmath])
        install_path = proj.install(libmath, PATHS["build"])
        test_install_path = proj.install(test, PATHS["build"])
        # Install
        sys.argv = ["", "install", "math"]
        cli(proj)
        assert os.path.exists(install_path)
        assert not os.path.exists(test_install_path)
        # Then remove
        sys.argv = ["", "uninstall", "-f", "math"]
        cli(proj)
        assert not os.path.exists(install_path)

    # TODO: Need coverage of install/uninstall for non-project-targets.

    def test_public_imports(self):
        import sbuildr
        from sbuildr import compiler, linker, BuildFlags, Project, Profile
