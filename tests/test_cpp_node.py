import srbuild.graph.cpp as cpp
from srbuild.tools import compiler, linker
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

    def build_utils_node(self):
        header_file = os.path.join(TEST_PROJECT_ROOT, "include", "utils.hpp")
        utils_header_node = cpp.SourceNode(path=header_file)
        return utils_header_node

    def build_test_node(self):
        utils_header_node = self.build_utils_node()
        header_file = os.path.join(TEST_PROJECT_ROOT, "test", "test.hpp")
        test_header_node = cpp.SourceNode(path=header_file, dirs=[os.path.join(TEST_PROJECT_ROOT, "include")], inputs=set([utils_header_node]))
        return test_header_node

    def build_object_graph(self, source_name):
        utils_header_node = self.build_utils_node()
        header_node = cpp.SourceNode(path=os.path.join(TEST_PROJECT_ROOT, "include", f"{source_name}.hpp"), dirs=[os.path.join(TEST_PROJECT_ROOT, "include")], inputs=set([utils_header_node]))
        source_path = os.path.join(TEST_PROJECT_ROOT, "src", f"{source_name}.cpp")
        source_node = cpp.SourceNode(path=source_path, dirs=[os.path.join(TEST_PROJECT_ROOT, "include")], inputs=set([header_node]))
        opts = set(["--std=c++17"])
        comp = compiler.clang
        output_path = os.path.join(TEST_PROJECT_BUILD, f"{source_name}.{comp.signature(opts)}.o")
        object_node = cpp.ObjectNode(inputs=set([source_node]), compiler=comp, output_path=output_path, opts=opts)
        return object_node

    def test_nested_source_node_has_dirs(self):
        test_header_node = self.build_test_node()
        test_header_node.build()
        self.assertTrue(os.path.join(TEST_PROJECT_ROOT, "include") in test_header_node.include_dirs)

    def test_factorial_object_node_compiles(self):
        # Direct header dependency and source file.
        factorial_object_node = self.build_object_graph("factorial")
        # Object node.
        self.assertTrue("factorial" in factorial_object_node.path)
        self.assertTrue(os.path.splitext(factorial_object_node.path)[1] == ".o")
        factorial_object_node.build()
        self.assertTrue(os.path.exists(factorial_object_node.path))

    def test_libmath_links(self):
        factorial_object_node = self.build_object_graph("factorial")
        fibonacci_object_node = self.build_object_graph("fibonacci")
        link = linker.clang
        output_path = os.path.join(TEST_PROJECT_BUILD, "libmath.so")
        opts = set(["--std=c++17", "-flto"])
        libmath_node = cpp.DynamicLibraryNode(inputs=set([factorial_object_node, fibonacci_object_node]), linker=link, output_path=output_path, opts=opts)
        libmath_node.build()
        self.assertTrue(os.path.exists(libmath_node.path))

    def tearDown(self):
        shutil.rmtree(TEST_PROJECT_BUILD)
