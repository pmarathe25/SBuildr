from sbuildr.dependencies.dependency import Dependency
from sbuildr.dependencies.meta import DependencyMetadata
from sbuildr.dependencies.fetchers.git_fetcher import GitFetcher
from sbuildr.dependencies.fetchers.copy_fetcher import CopyFetcher
from sbuildr.dependencies.builders.sbuildr_builder import SBuildrBuilder
from sbuildr.logger import G_LOGGER
import sbuildr.logger as logger
from sbuildr.misc import paths
from test_tools import PATHS, ROOT, TESTS_ROOT

import subprocess
import tempfile
import filecmp
import pytest
import shutil
import sys
import os

G_LOGGER.verbosity = logger.Verbosity.VERBOSE

SBUILDR_ROOT = os.path.abspath(os.path.join(TESTS_ROOT, os.path.pardir))
sys.path.insert(0, SBUILDR_ROOT)

class TestGitFetcher(object):
    def setup_method(self):
        self.commit_hash = "30432610248d95db23c801cabfa6205fe84b1b27"
        self.fetcher = GitFetcher(url="https://github.com/pmarathe25/SLog.git", tag="v0.2.0")
        assert self.fetcher.dependency_name == "SLog"

    def test_can_fetch_stest_repo(self):
        with tempfile.TemporaryDirectory() as install_dir:
            self.fetcher.set_dest_dir(install_dir)
            self.fetcher.fetch()

            head_status = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, cwd=install_dir)
            commit_hash = head_status.stdout.strip().decode(sys.stdout.encoding)

            assert commit_hash == self.commit_hash
            assert os.path.exists(install_dir)
            assert os.path.exists(os.path.join(install_dir, "build.py"))
            assert os.path.exists(os.path.join(install_dir, "include", "SLog.hpp"))

    def test_can_fetch_different_commits(self):
        fetcher2_commit_hash = "0d68ee3694c3c8350971fe0833db49aa10947670"
        fetcher2 = GitFetcher(url="https://github.com/pmarathe25/SLog.git", tag="v0.1.0")
        with tempfile.TemporaryDirectory() as install_dir:
            self.fetcher.set_dest_dir(install_dir)
            self.fetcher.fetch()

            fetcher2.set_dest_dir(install_dir)
            fetcher2.fetch()

            head_status = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, cwd=install_dir)
            commit_hash = head_status.stdout.strip().decode(sys.stdout.encoding)
            assert commit_hash == fetcher2_commit_hash

class TestCopyFetcher(object):
    def setup_method(self):
        self.fetcher = CopyFetcher(ROOT)
        assert self.fetcher.dependency_name == "minimal_project"

    def test_can_fetch_minimal_project(self):
        with tempfile.TemporaryDirectory() as install_dir:
            self.fetcher.set_dest_dir(install_dir)
            self.fetcher.fetch()
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

    def teardown_method(self):
        shutil.rmtree(PATHS["build"], ignore_errors=True)

class TestDependency(object):
    def setup_method(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.dependency = Dependency(CopyFetcher(ROOT), SBuildrBuilder(), cache_root=self.tmpdir.name)

    def test_can_setup_correctly(self):
        meta = self.dependency.setup()
        assert meta.META_API_VERSION == DependencyMetadata.META_API_VERSION
        # Source should be fetched into the cache root.
        assert os.path.exists(os.path.join(self.tmpdir.name, Dependency.CACHE_SOURCES_SUBDIR, "minimal_project"))
        # Libs/headers should be installed into the package root.
        assert os.path.exists(os.path.join(self.dependency.package_root, Dependency.PACKAGE_LIBRARY_SUBDIR, paths.name_to_libname("math")))
        assert os.path.exists(os.path.join(self.dependency.include_dir(), "math.hpp"))

    def test_string_function_works(self):
        assert str(self.dependency) == f"minimal_project: Version None in {self.dependency.package_root}"

class TestDependencyMetadata(object):
    def setup_method(self):
        self.dummy_meta = DependencyMetadata({}, [])

    def test_api_version_preserved_on_save(self):
        self.dummy_meta.META_API_VERSION = -1
        f = tempfile.NamedTemporaryFile()
        self.dummy_meta.save(f.name)
        loaded_meta = DependencyMetadata.load(f.name)
        assert os.path.exists(f.name) and loaded_meta.META_API_VERSION == self.dummy_meta.META_API_VERSION
        assert loaded_meta.META_API_VERSION != DependencyMetadata.META_API_VERSION
