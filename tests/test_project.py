from sbuildr.project.file_manager import FileManager
from sbuildr.project.project import Project
from sbuildr.graph.node import Library
from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.logger import G_LOGGER
import sbuildr.logger as logger

from test_tools import PATHS, TESTS_ROOT, ROOT

import tempfile
import shutil
import glob
import os

G_LOGGER.verbosity = logger.Verbosity.VERBOSE

class TestProject(object):
    def setup_method(self):
        self.project = Project(root=ROOT, build_dir=PATHS["build"])
        self.lib = self.project.library("test", sources=["factorial.cpp", "fibonacci.cpp"], libs=[Library("stdc++")])
        self.test = self.project.executable("test", sources=["tests/test.cpp"], libs=[Library("stdc++"), self.lib])

    def teardown_method(self):
        shutil.rmtree(self.project.build_dir, ignore_errors=True)

    def check_target(self, target):
        for name in self.project.profiles.keys():
            assert name in target
        for profile_name, node in target.items():
            # Make sure generated files are in the build directory.
            build_dir = self.project.profile(profile_name).build_dir
            assert os.path.dirname(node.path) == build_dir
            assert all([os.path.dirname(inp.path) == build_dir or os.path.dirname(inp.path) == self.project.common_build_dir for inp in node.inputs])

    def test_inits_to_curdir(self):
        proj = Project()
        assert proj.files.root_dir == os.path.dirname(__file__)

    def test_executable_api(self):
        self.project.configure()
        self.check_target(self.test)

    def test_library_api(self):
        self.project.configure()
        for node in self.lib.values():
            assert node.flags._shared
        self.check_target(self.lib)

    def test_configure_defaults(self):
        self.project.configure()
        # The project's graph is complete at this stage, and should include all the files in PATHS, plus libraries.
        for path in PATHS.values():
            if os.path.isfile(path):
                assert self.project.graph.contains_path(path)
        # Libraries without associated paths should not be in the project graph.
        assert not self.project.graph.contains_path("stdc++")
        for target in self.project.all_targets():
            for node in target.values():
                assert self.project.graph.contains_path(node.path)
                # Non-path libraries should have been removed as node inputs
                for inp in node.inputs:
                    if isinstance(inp, Library):
                        assert inp.name != "stdc++"
        assert os.path.exists(self.project.backend.config_file)

    def build(self):
        self.project.configure()
        self.project.build()

    def test_default_build(self):
        self.build()
        for target in self.project.all_targets():
            for node in target.values():
                assert os.path.exists(node.path)

    def test_default_clean_dry_run(self):
        self.build()
        self.project.clean()
        for target in self.project.all_targets():
            for node in target.values():
                assert os.path.exists(node.path)

    def test_default_clean(self):
        self.build()
        self.project.clean(dry_run=False)
        for prof in self.project.profiles.values():
            assert not os.path.exists(prof.build_dir)

    def test_single_profile_clean(self):
        self.build()
        clean_profs = ["release"]
        self.project.clean(profile_names=clean_profs, dry_run=False)
        for name, prof in self.project.profiles.items():
            build_dir_exists = os.path.exists(prof.build_dir)
            if name in clean_profs:
                assert not build_dir_exists
            else:
                assert build_dir_exists

    def test_api_version_preserved_on_save(self):
        self.project.PROJECT_API_VERSION = -1
        f = tempfile.NamedTemporaryFile()
        self.project.export(f.name)
        loaded_project = Project.load(f.name)
        assert loaded_project.PROJECT_API_VERSION == self.project.PROJECT_API_VERSION
        assert loaded_project.PROJECT_API_VERSION != Project.PROJECT_API_VERSION

    # TODO: Test run, run_tests, install, uninstall

class TestFileManager(object):
    def setup_method(self):
        self.manager = FileManager(ROOT)
        self.manager.add_writable_dir(self.manager.add_exclude_dir(PATHS["build"]))

    def test_add_include_dir(self):
        self.manager.add_include_dir(PATHS["include"])
        assert self.manager.include_dirs == [PATHS["include"]]

    def test_globs_files_from_relpath_into_abspaths(self):
        dirs = [os.path.relpath(os.path.join(os.path.dirname(__file__), "minimal_project"))]
        manager = FileManager(ROOT, dirs=dirs)
        manager.add_exclude_dir(PATHS["build"])
        all_files = set()
        for file in glob.iglob(os.path.join(ROOT, "**"), recursive=True):
            if os.path.isfile(file):
                all_files.add(os.path.abspath(file))
        print(all_files)
        assert manager.files == all_files
        assert all([os.path.isabs(file) for file in manager.files])

    def test_find(self):
        for filename, path in PATHS.items():
            if os.path.isfile(path):
                assert self.manager.find(filename) == [path]

    def test_can_find_sources(self):
        node = self.manager.source("tests/test.cpp")
        assert node.path == PATHS["test.cpp"]

    def test_source(self):
        factorial_hpp = self.manager.source(PATHS["factorial.hpp"])
        fibonacci_hpp = self.manager.source(PATHS["fibonacci.hpp"])
        factorial_cpp = self.manager.source(PATHS["factorial.cpp"])
        fibonacci_cpp = self.manager.source(PATHS["fibonacci.cpp"])
        test_cpp = self.manager.source(PATHS["test.cpp"])
        self.manager.scan_all()
        # Headers
        # Includes utils.hpp..
        assert factorial_hpp.include_dirs == sorted([PATHS["src"], PATHS["include"]])
        # Includes utils.hpp, but using a path starting with src/
        assert fibonacci_hpp.include_dirs == sorted([ROOT, PATHS["include"]])
        # CPP files
        # Includes factorial.hpp
        assert factorial_cpp.include_dirs == sorted(set([PATHS["src"]] + factorial_hpp.include_dirs))
        # Includes fibonacci.hpp
        assert fibonacci_cpp.include_dirs == sorted(set([PATHS["src"]] + fibonacci_hpp.include_dirs))
        # Test files
        # Includes utils.hpp
        # Includes utils.hpp, factorial.hpp and fibonacci.hpp
        # Also includes iostream, which the logger should mention as not found.
        assert test_cpp.include_dirs == sorted(set([PATHS["src"]] + fibonacci_hpp.include_dirs + factorial_hpp.include_dirs))
        # Make sure that the source graph has been populated
        for file in ["factorial.hpp", "fibonacci.hpp", "test.cpp", "factorial.cpp", "fibonacci.cpp", "utils.hpp"]:
            assert self.manager.graph.contains_path(PATHS[file])
