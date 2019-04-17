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

    def test_include_dirs(self):
        manager = FileManager(dirs=[ROOT])
        # Headers
        # Includes utils.hpp, but using a path starting with minimal_project/
        factorial_hpp_includes = manager.include_dirs(PATHS["factorial.hpp"])
        assert factorial_hpp_includes == set([TESTS_ROOT])
        # Includes utils.hpp, but using a path starting with include/
        fibonacci_hpp_includes = manager.include_dirs(PATHS["fibonacci.hpp"])
        assert fibonacci_hpp_includes == set([ROOT])
        # CPP files
        # Includes factorial.hpp
        factorial_cpp_includes = manager.include_dirs(PATHS["factorial.cpp"])
        assert factorial_cpp_includes == set([PATHS["include"]]) | factorial_hpp_includes
        # Includes fibonacci.hpp
        fibonacci_cpp_includes = manager.include_dirs(PATHS["fibonacci.cpp"])
        assert fibonacci_cpp_includes == set([PATHS["include"]]) | fibonacci_hpp_includes
        # Test files
        # Includes utils.hpp
        test_hpp_includes = manager.include_dirs(PATHS["test.hpp"])
        assert test_hpp_includes == set([PATHS["include"]])
        # Includes utils.hpp, test.hpp, factorial.hpp and fibonacci.hpp
        # Also includes iostream, which the logger should mention as not found.
        assert manager.include_dirs(PATHS["test.cpp"]) == set([PATHS["include"], PATHS["test"]]) | test_hpp_includes | fibonacci_hpp_includes | factorial_hpp_includes
