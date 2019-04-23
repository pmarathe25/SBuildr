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
        assert proj.files.root_dir == os.path.dirname(__file__)

    def test_can_find_sources(self):
        proj = Project(root=ROOT)
        nodes = proj._get_source_nodes(sources=["test/test.cpp"])
        source_paths = [node.path for node in nodes]
        assert source_paths == [PATHS["test.cpp"]]

    def test_executable_api(self):
        proj = Project(root=ROOT)
        test = proj.executable("test", sources=["test/test.cpp"], libs=["stdc++"])
        for name in proj.profiles.keys():
            assert name in test

class TestFileManager(object):
    def test_globs_files_from_relpath_into_abspaths(self):
        dirs = [os.path.relpath(os.path.join(os.path.dirname(__file__), "minimal_project"))]
        manager = FileManager(ROOT, PATHS["build"], dirs=dirs)
        all_files = []
        for file in glob.iglob(os.path.join(ROOT, "**"), recursive=True):
            if os.path.isfile(file):
                all_files.append(os.path.abspath(file))
        print(all_files)
        assert manager.files == all_files
        assert all([os.path.isabs(file) for file in manager.files])

    def test_find(self):
        manager = FileManager(ROOT, PATHS["build"], dirs=[ROOT])
        for filename, path in PATHS.items():
            if os.path.isfile(path):
                assert manager.find(filename) == [path]

    def test_source(self):
        manager = FileManager(ROOT, PATHS["build"], dirs=[ROOT])
        factorial_hpp = manager.source(PATHS["factorial.hpp"])
        fibonacci_hpp = manager.source(PATHS["fibonacci.hpp"])
        factorial_cpp = manager.source(PATHS["factorial.cpp"])
        fibonacci_cpp = manager.source(PATHS["fibonacci.cpp"])
        test_hpp = manager.source(PATHS["test.hpp"])
        test_cpp = manager.source(PATHS["test.cpp"])
        manager.scan_all()
        # Headers
        # Includes utils.hpp, but using a path starting with minimal_project/
        assert factorial_hpp.include_dirs == sorted([TESTS_ROOT])
        # Includes utils.hpp, but using a path starting with include/
        assert fibonacci_hpp.include_dirs == sorted([ROOT])
        # CPP files
        # Includes factorial.hpp
        assert factorial_cpp.include_dirs == sorted(set([PATHS["include"]] + factorial_hpp.include_dirs))
        # Includes fibonacci.hpp
        assert fibonacci_cpp.include_dirs == sorted(set([PATHS["include"]] + fibonacci_hpp.include_dirs))
        # Test files
        # Includes utils.hpp
        assert test_hpp.include_dirs == sorted([PATHS["include"]])
        # Includes utils.hpp, test.hpp, factorial.hpp and fibonacci.hpp
        # Also includes iostream, which the logger should mention as not found.
        assert test_cpp.include_dirs == sorted(set([PATHS["include"], PATHS["test"]] + test_hpp.include_dirs + fibonacci_hpp.include_dirs + factorial_hpp.include_dirs))
        # Make sure that the source graph has been populated
        for file in ["factorial.hpp", "fibonacci.hpp", "test.hpp", "test.cpp", "factorial.cpp", "fibonacci.cpp", "utils.hpp"]:
            assert PATHS[file] in manager.source_graph
