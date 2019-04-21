from srbuild.project.file_manager import FileManager
from srbuild.project.project import Project
from srbuild.logger import G_LOGGER
from test_tools import PATHS, TESTS_ROOT, ROOT
import glob
import os

G_LOGGER.severity = G_LOGGER.VERBOSE

class TestProject(object):
    def test_inits_to_curdir(self):
        proj = Project()
        assert proj.root_dir == os.path.dirname(__file__)

class TestFileManager(object):
    def test_globs_files_from_relpath_into_abspaths(self):
        manager = FileManager(dirs=[os.path.relpath(os.path.join(os.path.dirname(__file__), "minimal_project"))])
        all_files = []
        for file in glob.iglob(os.path.join(ROOT, "**"), recursive=True):
            if os.path.isfile(file):
                all_files.append(os.path.abspath(file))
        assert manager.files == all_files
        assert all([os.path.isabs(file) for file in manager.files])

    def test_find(self):
        manager = FileManager(dirs=[ROOT])
        for filename, path in PATHS.items():
            if os.path.isfile(path):
                assert manager.find(filename) == [path]

    def test_add_source(self):
        manager = FileManager(dirs=[ROOT])
        # Headers
        # Includes utils.hpp, but using a path starting with minimal_project/
        manager.add_source(PATHS["factorial.hpp"])
        factorial_hpp_includes = manager.includes(PATHS["factorial.hpp"])
        assert factorial_hpp_includes == sorted([TESTS_ROOT])
        # Includes utils.hpp, but using a path starting with include/
        manager.add_source(PATHS["fibonacci.hpp"])
        fibonacci_hpp_includes = manager.includes(PATHS["fibonacci.hpp"])
        assert fibonacci_hpp_includes == sorted([ROOT])
        # CPP files
        # Includes factorial.hpp
        manager.add_source(PATHS["factorial.cpp"])
        factorial_cpp_includes = manager.includes(PATHS["factorial.cpp"])
        assert factorial_cpp_includes == sorted(set([PATHS["include"]] + factorial_hpp_includes))
        # Includes fibonacci.hpp
        manager.add_source(PATHS["fibonacci.cpp"])
        fibonacci_cpp_includes = manager.includes(PATHS["fibonacci.cpp"])
        assert fibonacci_cpp_includes == sorted(set([PATHS["include"]] + fibonacci_hpp_includes))
        # Test files
        # Includes utils.hpp
        manager.add_source(PATHS["test.hpp"])
        test_hpp_includes = manager.includes(PATHS["test.hpp"])
        assert test_hpp_includes == sorted([PATHS["include"]])
        # Includes utils.hpp, test.hpp, factorial.hpp and fibonacci.hpp
        # Also includes iostream, which the logger should mention as not found.
        manager.add_source(PATHS["test.cpp"])
        assert manager.includes(PATHS["test.cpp"]) == sorted(set([PATHS["include"], PATHS["test"]] + test_hpp_includes + fibonacci_hpp_includes + factorial_hpp_includes))
        # Make sure that the source graph has been populated
        for file in ["factorial.hpp", "fibonacci.hpp", "test.hpp", "test.cpp", "factorial.cpp", "fibonacci.cpp", "utils.hpp"]:
            assert PATHS[file] in manager.source_graph
