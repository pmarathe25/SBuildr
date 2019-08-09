from sbuildr.project.dependencies.fetchers.git_fetcher import GitFetcher
from sbuildr.project.dependencies.fetchers.copy_fetcher import CopyFetcher
from sbuildr.project.dependencies.builders.sbuildr_builder import SBuildrBuilder
from sbuildr.misc import paths
from test_tools import PATHS, ROOT, TESTS_ROOT

import tempfile
import filecmp
import pytest
import os

class TestGitFetcher(object):
    def setup_method(self):
        self.commit_hash = "b2dd61e5669f9a2dee75d55eaf2950a722eebeae"
        self.fetcher = GitFetcher(url="https://github.com/pmarathe25/SLog.git", commit=self.commit_hash)
        assert self.fetcher.dependency_name == "SLog"

    def test_can_fetch_stest_repo(self):
        with tempfile.TemporaryDirectory() as install_dir:
            tag = self.fetcher.fetch(install_dir)
            assert tag == self.commit_hash
            assert os.path.exists(install_dir)
            assert os.path.exists(os.path.join(install_dir, "build.py"))
            assert os.path.exists(os.path.join(install_dir, "include", "SLog.hpp"))

class TestCopyFetcher(object):
    def setup_method(self):
        self.fetcher = CopyFetcher(ROOT)
        assert self.fetcher.dependency_name == "minimal_project"

    def test_can_fetch_minimal_project(self):
        with tempfile.TemporaryDirectory() as install_dir:
            tag = self.fetcher.fetch(install_dir)
            assert os.path.exists(install_dir)
            dircmp = filecmp.dircmp(ROOT, install_dir)
            assert not dircmp.left_only
            assert not dircmp.right_only

class TestSBuildrBuilder(object):
    def setup_method(self):
        self.builder = SBuildrBuilder()
        self.output_dir = tempfile.TemporaryDirectory()
        self.header_dir = os.path.join(self.output_dir.name, "include")
        self.lib_dir = os.path.join(self.output_dir.name, "lib")
        self.exec_dir = os.path.join(self.output_dir.name, "bin")
        os.makedirs(self.header_dir)
        os.makedirs(self.lib_dir)
        os.makedirs(self.exec_dir)

    def test_can_build_example_repo(self):
        self.builder.install(ROOT, self.header_dir, self.lib_dir, self.exec_dir)
        assert os.path.exists(os.path.join(self.header_dir, "math.hpp"))
        assert os.path.exists(os.path.join(self.lib_dir, paths.name_to_libname("math")))
