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

class TestSBuildrExecutable(object):
    def setup_method(self):
        print(f"Creating build directory: {PATHS['build']}")
        os.makedirs(PATHS["build"], exist_ok=True)
        self.proj = Project(root=ROOT, build_dir=PATHS["build"])
        self.libmath = self.proj.library("math", sources=["factorial.cpp", "fibonacci.cpp"], libs=[Library("stdc++")])
        self.exec = self.proj.executable("exec", sources=["test.cpp"], libs=[Library("stdc++"), self.libmath])
        self.test = self.proj.test("test", sources=["test.cpp"], libs=[Library("stdc++"), self.libmath])
        [self.header] = self.proj.interfaces(["math.hpp"])
        self.saved_project = tempfile.NamedTemporaryFile()
        self.proj.find_dependencies()
        self.proj.configure_graph()
        self.proj.configure_backend()
        self.proj.export(self.saved_project.name)

    def teardown_method(self):
        print(f"Removing build directory: {PATHS['build']}")
        shutil.rmtree(PATHS["build"], ignore_errors=True)

    # TODO: Test clean

    def check_subprocess(self, status):
        assert not status.returncode

    def check_subprocess_fails(self, status):
        assert status.returncode

    def test_no_args(self):
        self.check_subprocess(subprocess.run([SBUILDR_EXEC]))

    def test_configure(self):
        project_file = os.path.join(PATHS["build"], Project.DEFAULT_SAVED_PROJECT_NAME)
        build_script = os.path.join(ROOT, "build.py")
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", project_file, "configure", "-b", build_script]))
        assert os.path.exists(project_file)

    def test_configure_complains_about_build_script(self):
        project_file = os.path.join(PATHS["build"], Project.DEFAULT_SAVED_PROJECT_NAME)
        status = subprocess.run([SBUILDR_EXEC, "-p", project_file, "configure"], capture_output=True)
        assert b"Specified build script: " in status.stdout and b"does not exist" in status.stdout

    def test_help_targets(self):
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "help"]))

    def test_can_default_build_project(self):
        # Build both targets for all profiles.
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "build"]))
        # Ensure that the targets now exist
        for target in self.proj.all_targets():
            for node in target.values():
                assert os.path.exists(node.path)

    def test_can_build_selective_targets(self):
        # Build one targets for one profile.
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "build", self.libmath.name, "--release"]))
        # Ensure that the targets now exist
        for target in self.proj.all_targets():
            for prof_name, node in target.items():
                if prof_name == "release" and node.name == self.libmath.name:
                    assert os.path.exists(node.path)
                else:
                    assert not os.path.exists(node.path)

    def test_default_install_project(self):
        install_path = os.path.join(PATHS["build"], os.path.basename(self.libmath["release"].path))
        # Install release profile
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f"] + INSTALL_DIR_ARGS))
        assert os.path.exists(install_path)
        # Then remove
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f"] + INSTALL_DIR_ARGS))
        assert not os.path.exists(install_path)

    # Installation when profile is specified
    def test_profile_install_project(self):
        install_path = os.path.join(PATHS["build"], os.path.basename(self.libmath["debug"].path))
        release_install = os.path.join(PATHS["build"], os.path.basename(self.libmath["release"].path))
        # Install
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f", "--debug"] + INSTALL_DIR_ARGS))
        assert os.path.exists(install_path)
        assert not os.path.exists(release_install)
        # Then remove
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f", "--debug"] + INSTALL_DIR_ARGS))
        assert not os.path.exists(install_path)

    # Installation when target is specified
    def test_target_install_project(self):
        install_path = os.path.join(PATHS["build"], os.path.basename(self.libmath["release"].path))
        test_install_path = os.path.join(PATHS["build"], os.path.basename(self.exec["release"].path))
        # Install
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f", "math"] + INSTALL_DIR_ARGS))
        assert os.path.exists(install_path)
        assert not os.path.exists(test_install_path)
        # Then remove
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f", "math"] + INSTALL_DIR_ARGS))
        assert not os.path.exists(install_path)

    # Installation when no installation targets are specified.
    def test_empty_install(self):
        proj = Project(root=ROOT)
        proj.export(self.saved_project.name)
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f"]))

    def test_header_install(self):
        # Check that the return value is the correct path
        assert self.header == PATHS["math.hpp"]

        install_path = os.path.join(PATHS["build"], "math.hpp")
        # Install
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "install", "-f"] + INSTALL_DIR_ARGS))
        assert os.path.exists(install_path)
        # Then remove
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "uninstall", "-f"] + INSTALL_DIR_ARGS))
        assert not os.path.exists(install_path)

    def test_run_with_no_targets_complains(self):
        self.check_subprocess_fails(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "run"]))

    def test_run_with_single_target(self):
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "run", self.exec.name]))

    def test_run_fails_to_run_test(self):
        self.check_subprocess_fails(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "run", self.test.name]))

    def test_default_test(self):
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "test"]))

    def test_selected_test(self):
        self.check_subprocess(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "test", self.test.name]))

    def test_test_fails_to_run_executable(self):
        self.check_subprocess_fails(subprocess.run([SBUILDR_EXEC, "-p", self.saved_project.name, "test", self.exec.name]))
