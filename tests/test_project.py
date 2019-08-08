from sbuildr.project.file_manager import FileManager
from sbuildr.project.project import Project
from sbuildr.logger import G_LOGGER
import sbuildr.logger as logger

from test_tools import PATHS, TESTS_ROOT, ROOT

import glob
import os

G_LOGGER.verbosity = logger.Verbosity.VERBOSE

# TODO: Move test_integration test into here.
class TestProject(object):
    def test_inits_to_curdir(self):
        proj = Project()
        assert proj.files.root_dir == os.path.dirname(__file__)

    def check_target(self, proj, target):
        for name in proj.profiles.keys():
            assert name in target
        for profile_name, node in target.items():
            # Make sure generated files are in the build directory.
            build_dir = proj.profile(profile_name).build_dir
            assert os.path.dirname(node.path) == build_dir
            assert all([os.path.dirname(inp.path) == build_dir or os.path.dirname(inp.path) == proj.common_objs_build_dir for inp in node.inputs])

    def test_executable_api(self):
        proj = Project(root=ROOT)
        test = proj.executable("test", sources=["tests/test.cpp"], libs=["stdc++"])
        self.check_target(proj, test)

    def test_library_api(self):
        proj = Project(root=ROOT)
        lib = proj.library("test", sources=["factorial.cpp", "fibonacci.cpp"], libs=["stdc++"])
        for node in lib.values():
            assert node.flags._shared
        self.check_target(proj, lib)

class TestFileManager(object):
    def setup_method(self):
        self.manager = FileManager(ROOT)
        self.manager.add_build_dir(PATHS["build"])

    def test_globs_files_from_relpath_into_abspaths(self):
        dirs = [os.path.relpath(os.path.join(os.path.dirname(__file__), "minimal_project"))]
        manager = FileManager(ROOT, dirs=dirs)
        manager.add_build_dir(PATHS["build"])
        all_files = []
        for file in glob.iglob(os.path.join(ROOT, "**"), recursive=True):
            if os.path.isfile(file):
                all_files.append(os.path.abspath(file))
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
