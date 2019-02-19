import sbuild.graph.cpp as cpp
import sbuild.tools.compiler as compiler
import unittest
import shutil
import os

TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))
TEST_PROJECT_ROOT = os.path.join(TESTS_ROOT, "minimal_project")
TEST_PROJECT_BUILD = os.path.join(TEST_PROJECT_ROOT, "build")

class TestCppNodes(unittest.TestCase):
    def setUp(self):
        self.include_dirs = [os.path.join(TEST_PROJECT_ROOT, "include")]
        os.mkdir(TEST_PROJECT_BUILD)
        os.makedirs(os.path.join(TEST_PROJECT_BUILD, "objs"), exist_ok=True)
        os.makedirs(os.path.join(TEST_PROJECT_BUILD, "libs"), exist_ok=True)

    def test_single_source_node_has_dirs(self):
        utils_header = os.path.join(TEST_PROJECT_ROOT, "include", "utils.hpp")
        utils_header_node = cpp.HeaderNode(path=utils_header)
        self.assertTrue(os.path.join(TEST_PROJECT_ROOT, "include") in utils_header_node.dirs)

    def test_nested_source_node_has_dirs(self):
        utils_header = os.path.join(TEST_PROJECT_ROOT, "include", "utils.hpp")
        utils_header_node = cpp.HeaderNode(path=utils_header)
        # This header should include the
        test_header = os.path.join(TEST_PROJECT_ROOT, "test", "test.hpp")
        test_header_node = cpp.HeaderNode(path=test_header, inputs=set([utils_header_node]))
        self.assertTrue(os.path.join(TEST_PROJECT_ROOT, "include") in test_header_node.dirs)
        self.assertTrue(os.path.join(TEST_PROJECT_ROOT, "test") in test_header_node.dirs)

    def test_factorial_object_node_compiles(self):
        # Nested header dependency.
        utils_header = os.path.join(TEST_PROJECT_ROOT, "include", "utils.hpp")
        utils_header_node = cpp.HeaderNode(path=utils_header)
        # Direct header dependency.
        factorial_header = os.path.join(TEST_PROJECT_ROOT, "include", "factorial.hpp")
        factorial_header_node = cpp.HeaderNode(path=factorial_header, inputs=set([utils_header_node]))
        # CPP
        source_path = os.path.join(TEST_PROJECT_ROOT, "src", "factorial.cpp")
        cpp_node = cpp.SourceNode(path=source_path, inputs=set([factorial_header_node]))
        # Object node.
        opts = set(["--std=c++17"])
        obj_node = cpp.ObjectNode(inputs=set([cpp_node]), compiler=compiler.clang, opts=opts)
        self.assertTrue("factorial" in obj_node.path)
        self.assertTrue(os.path.splitext(obj_node.path)[1] == ".o")
        obj_node.build()
        self.assertTrue(os.path.exists(obj_node.path))

    def tearDown(self):
        shutil.rmtree(TEST_PROJECT_BUILD)
