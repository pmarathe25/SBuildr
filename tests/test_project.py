from sbuildr.project.file_manager import FileManager
from sbuildr.project.project import Project
from sbuildr.graph.node import Library
from sbuildr.backends.rbuild import RBuildBackend
from sbuildr.logger import G_LOGGER
import sbuildr.logger as logger

from test_tools import PATHS, TESTS_ROOT, ROOT

import shutil
import glob
import os

G_LOGGER.verbosity = logger.Verbosity.VERBOSE

# TODO: Move test_integration tests into here.
class TestProject(object):
    def setup_method(self):
        self.project = Project(root=ROOT, build_dir=PATHS["build"])
        self.lib = self.project.library("test", sources=["factorial.cpp", "fibonacci.cpp"], libs=[Library("stdc++")])
        self.test = self.project.executable("test", sources=["tests/test.cpp"], libs=[Library("stdc++"), self.lib])

    def teardown_method(self):
        shutil.rmtree(self.project.build_dir, ignore_errors=True)

    def check_target(self, proj, target):
        for name in proj.profiles.keys():
            assert name in target
        for profile_name, node in target.items():
            # Make sure generated files are in the build directory.
            build_dir = proj.profile(profile_name).build_dir
            assert os.path.dirname(node.path) == build_dir
            assert all([os.path.dirname(inp.path) == build_dir or os.path.dirname(inp.path) == proj.common_objs_build_dir for inp in node.inputs])

    def test_inits_to_curdir(self):
        proj = Project()
        assert proj.files.root_dir == os.path.dirname(__file__)

    def test_executable_api(self):
        self.project.configure_graph()
        self.check_target(self.project, self.test)

    def test_library_api(self):
        self.project.configure_graph()
        for node in self.lib.values():
            assert node.flags._shared
        self.check_target(self.project, self.lib)

    def test_fetch_dependencies_default(self):
        self.project.fetch_dependencies()

    def test_configure_graph(self):
        self.project.fetch_dependencies()
        self.project.configure_graph()
        # The project's graph is complete at this stage, and should include all the files in PATHS, plus libraries.
        for path in PATHS.values():
            if os.path.isfile(path):
                assert path in self.project.graph
        # Libraries without associated paths should not be in the project graph.
        assert "stdc++" not in self.project.graph
        for target in self.project.all_targets():
            for node in target.values():
                assert node.path in self.project.graph
                # Non-path libraries should have been removed as node inputs
                for inp in node.inputs:
                    if isinstance(inp, Library):
                        assert inp.name != "stdc++"

    def test_configure_default_backend(self):
        self.project.fetch_dependencies()
        self.project.configure_graph()
        self.project.configure_backend()
        assert os.path.exists(self.project.backend.config_file)

    def test_build(self):
        self.project.fetch_dependencies()
        self.project.configure_graph()
        self.project.configure_backend()
        self.project.build()
        for target in self.proj.all_targets():
            for node in target.values():
                assert os.path.exists(node.path)

    # TODO: Test run, run_tests, install, uninstall, clean

class TestFileManager(object):
    def setup_method(self):
        self.manager = FileManager(ROOT)
        self.manager.add_writable_dir(self.manager.add_exclude_dir(PATHS["build"]))

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
            assert PATHS[file] in self.manager.graph
