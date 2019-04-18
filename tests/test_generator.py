from srbuild.graph.node import Node
from srbuild.graph.graph import Graph
from srbuild.generator import rbuild
from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from test_tools import PATHS, compile_cmd, link_cmd
import subprocess
import shutil
import pytest
import os

def generate_build_graph(compiler, linker):
    # Headers
    utils_h = Node(PATHS["utils.hpp"])
    factorial_h = Node(PATHS["factorial.hpp"], [utils_h])
    fibonacci_h = Node(PATHS["fibonacci.hpp"], [utils_h])
    test_h = Node(PATHS["test.hpp"], [utils_h])
    # Source files
    factorial_cpp = Node(PATHS["factorial.cpp"], [factorial_h])
    fibonacci_cpp = Node(PATHS["fibonacci.cpp"], [fibonacci_h])
    test_cpp = Node(PATHS["test.cpp"], [test_h])
    # Object files
    cmd, _ = compile_cmd(compiler, factorial_cpp.path)
    factorial_o = Node(os.path.join(PATHS["build"], "factorial.o"), [factorial_cpp], cmds=[cmd])
    cmd, _ = compile_cmd(compiler, fibonacci_cpp.path)
    fibonacci_o = Node(os.path.join(PATHS["build"], "fibonacci.o"), [fibonacci_cpp], cmds=[cmd])
    cmd, _ = compile_cmd(compiler, test_cpp.path)
    test_o = Node(os.path.join(PATHS["build"], "test.o"), [test_cpp], cmds=[cmd])
    # Library and executable
    cmd, _ = link_cmd(linker, [factorial_o.path, fibonacci_o.path, "-lstdc++"], "libmath.so", flags=BuildFlags().shared())
    libmath = Node(os.path.join(PATHS["build"], "libmath.so"), [factorial_o, fibonacci_o], cmds=[cmd])
    cmd, _ = link_cmd(linker, [test_o.path, libmath.path, "-lstdc++"], "test")
    test = Node(os.path.join(PATHS["build"], "test"), [test_o, libmath], cmds=[cmd])
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
        config = rbuild.generate(graph)
        filepath = os.path.join(PATHS["build"], "rbuild")
        with open(filepath, "w") as f:
            f.write(config)
        assert subprocess.run(["rbuild", filepath])
        # All paths should exist after building.
        for node in graph.values():
            assert os.path.exists(node.path)
