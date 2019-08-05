from sbuildr.project.dependencies.fetchers.git_fetcher import GitFetcher
from sbuildr.project.dependencies.builders.sbuildr_builder import SBuildrBuilder
from sbuildr.misc import paths
from test_tools import PATHS, ROOT, TESTS_ROOT

import tempfile
import pytest
import os

class TestGitFetcher(object):
    def setup_method(self):
        self.commit_hash = "b2dd61e5669f9a2dee75d55eaf2950a722eebeae"
        self.fetcher = GitFetcher(url="https://github.com/pmarathe25/SLog.git", commit=self.commit_hash)

    def test_can_fetch_stest_repo(self):
        with tempfile.TemporaryDirectory() as install_dir:
            dep_info = self.fetcher.fetch(install_dir)
            assert dep_info.name == "SLog"
            assert dep_info.path == os.path.join(install_dir, "SLog")
            assert dep_info.version_tags == [self.commit_hash]
            assert os.path.exists(dep_info.path)

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
        self.builder.setup(ROOT, self.header_dir, self.lib_dir, self.exec_dir)
        assert os.path.exists(os.path.join(self.header_dir, "math.hpp"))
        assert os.path.exists(os.path.join(self.lib_dir, paths.libname("math")))
