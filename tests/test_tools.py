from sbuildr.tools import compiler, linker
from sbuildr.tools.flags import BuildFlags
from typing import List
import subprocess
import pytest
import shutil
import os

TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.join(TESTS_ROOT, "minimal_project")
PATHS = {
    "include": os.path.join(ROOT, "include"),
    "factorial.hpp": os.path.join(ROOT, "include", "factorial.hpp"),
    "fibonacci.hpp": os.path.join(ROOT, "include", "fibonacci.hpp"),
    "utils.hpp": os.path.join(ROOT, "include", "utils.hpp"),
    "factorial.cpp": os.path.join(ROOT, "src", "factorial.cpp"),
    "fibonacci.cpp": os.path.join(ROOT, "src", "fibonacci.cpp"),
    "test": os.path.join(ROOT, "test"),
    "test/test": os.path.join(ROOT, "test", "test"),
    "test.hpp": os.path.join(ROOT, "test", "test.hpp"),
    "test.cpp": os.path.join(ROOT, "test", "test.cpp"),
    # Output files
    "build": os.path.join(ROOT, "build"),
}

def compile_cmd(compiler, input_path: str, include_dirs: List[str]=[], flags: BuildFlags=BuildFlags()):
    flags += BuildFlags().O(3).std(17).march("native").fpic()
    include_dirs = include_dirs or [PATHS["include"], PATHS["test"], ROOT, TESTS_ROOT]
    # Get output path
    base = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(PATHS["build"], f"{base}.o")
    # Generate the command needed
    return compiler.compile(input_path, output_path, include_dirs, flags), output_path

def link_cmd(linker, input_paths, output_name, lib_dirs: List[str]=[], flags: BuildFlags=BuildFlags()):
    flags += BuildFlags().O(3).std(17).march("native").fpic()
    # Get output path
    output_path = os.path.join(PATHS["build"], output_name)
    # Generate the command needed
    return linker.link(input_paths, output_path, lib_dirs=lib_dirs, flags=flags), output_path

class TestCompilers(object):
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

    @staticmethod
    def compile(compiler, input_path: str, include_dirs: List[str]=[], flags: BuildFlags=BuildFlags()):
        cmd, output_path = compile_cmd(compiler, input_path, include_dirs, flags)
        print(f"Running command: {cmd}")
        subprocess.run(cmd)
        return output_path

    @pytest.mark.parametrize("compiler", [compiler.gcc, compiler.clang])
    @pytest.mark.parametrize("src_path", [PATHS["fibonacci.cpp"], PATHS["factorial.cpp"]])
    def test_can_compile(self, compiler, src_path):
        output_path = TestCompilers.compile(compiler, src_path)
        assert os.path.exists(output_path)

class TestLinkers(TestCompilers):
    @staticmethod
    def link(linker, input_paths, output_name, lib_dirs: List[str]=[], flags: BuildFlags=BuildFlags()):
        cmd, output_path = link_cmd(linker, input_paths, output_name, lib_dirs, flags)
        print(f"Running command: {cmd}")
        subprocess.run(cmd)
        return output_path

    @staticmethod
    def build_libtest(compiler, linker):
        fibonacci = TestLinkers.compile(compiler, PATHS["fibonacci.cpp"])
        factorial = TestLinkers.compile(compiler, PATHS["factorial.cpp"])
        return TestLinkers.link(linker, [fibonacci, factorial, "-lstdc++"], "libtest.so", flags=BuildFlags()._enable_shared())

    @pytest.mark.parametrize("compiler", [compiler.gcc, compiler.clang])
    @pytest.mark.parametrize("linker", [linker.gcc, linker.clang])
    def test_can_link_executable(self, compiler, linker):
        assert os.path.exists(TestLinkers.build_libtest(compiler, linker))

    @pytest.mark.parametrize("compiler", [compiler.gcc, compiler.clang])
    @pytest.mark.parametrize("linker", [linker.gcc, linker.clang])
    def test_can_link_library(self, compiler, linker):
        libtest = TestLinkers.build_libtest(compiler, linker)
        test = TestLinkers.compile(compiler, PATHS["test.cpp"])
        assert os.path.exists(TestLinkers.link(linker, [test, libtest, "-lstdc++"], "test"))
