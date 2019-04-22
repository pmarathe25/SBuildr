from srbuild.graph.node import Node, SourceNode, CompiledNode, LinkedNode
from srbuild.graph.graph import Graph
from srbuild.generator.rbuild import RBuildGenerator
from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from test_tools import PATHS, ROOT, TESTS_ROOT
import subprocess
import shutil
import pytest
import os

def generate_build_graph(compiler, linker):
    flags = BuildFlags().O(3).std(17).march("native").fpic()
    # Headers
    utils_h = SourceNode(PATHS["utils.hpp"])
    factorial_h = SourceNode(PATHS["factorial.hpp"], [utils_h])
    fibonacci_h = SourceNode(PATHS["fibonacci.hpp"], [utils_h])
    test_h = SourceNode(PATHS["test.hpp"], [utils_h])
    # Source files
    factorial_cpp = SourceNode(PATHS["factorial.cpp"], [factorial_h], include_dirs=[PATHS["include"], PATHS["test"], ROOT, TESTS_ROOT])
    fibonacci_cpp = SourceNode(PATHS["fibonacci.cpp"], [fibonacci_h], include_dirs=[PATHS["include"], PATHS["test"], ROOT, TESTS_ROOT])
    test_cpp = SourceNode(PATHS["test.cpp"], [test_h], include_dirs=[PATHS["include"], PATHS["test"], ROOT, TESTS_ROOT])
    # Object files
    factorial_o = CompiledNode(os.path.join(PATHS["build"], "factorial.o"), input=factorial_cpp, compiler=compiler, flags=flags)
    fibonacci_o = CompiledNode(os.path.join(PATHS["build"], "fibonacci.o"), input=fibonacci_cpp, compiler=compiler, flags=flags)
    test_o = CompiledNode(os.path.join(PATHS["build"], "test.o"), input=test_cpp, compiler=compiler, flags=flags)
    # Library and executable
    libmath = LinkedNode(os.path.join(PATHS["build"], "libmath.so"), [factorial_o, fibonacci_o], linker=linker, flags=flags+BuildFlags().shared(), libs=["stdc++"])
    test = LinkedNode(os.path.join(PATHS["build"], "test"), [test_o, libmath], linker=linker, flags=flags, libs=["stdc++"])
    return Graph([utils_h, factorial_h, fibonacci_h, test_h, factorial_cpp, fibonacci_cpp, test_cpp, factorial_o, fibonacci_o, test_o, libmath, test])

class TestRBuild(object):
    @classmethod
    def setup_class(cls):
        cls.teardown_class()
        print(f"Creating build directory: {PATHS['build']}")
        os.mkdir(PATHS["build"])

    @classmethod
    def teardown_class(cls):
        print(f"Removing build directory: {PATHS['build']}")
        try:
            shutil.rmtree(PATHS["build"])
        except FileNotFoundError:
            pass

    @pytest.mark.parametrize("compiler", [compiler.gcc, compiler.clang])
    @pytest.mark.parametrize("linker", [linker.gcc, linker.clang])
    def test_config_file(self, compiler, linker):
        graph = generate_build_graph(compiler, linker)
        config = RBuildGenerator().generate(graph)
        filepath = os.path.join(PATHS["build"], "rbuild")
        with open(filepath, "w") as f:
            f.write(config)
        assert subprocess.run(["rbuild", filepath])
        # All paths should exist after building.
        for node in graph.values():
            assert os.path.exists(node.path)
