from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from srbuild.logger import G_LOGGER
from typing import List
import subprocess
import pytest
import shutil
import os

ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), "minimal_project")
PATHS = {
    "include": os.path.join(ROOT, "include"),
    "test": os.path.join(ROOT, "test"),
    "fibonacci.cpp": os.path.join(ROOT, "src", "fibonacci.cpp"),
    "factorial.cpp": os.path.join(ROOT, "src", "factorial.cpp"),
    "test.cpp": os.path.join(ROOT, "test", "test.cpp"),
    # Output files
    "build": os.path.join(ROOT, "build"),
}
G_LOGGER.severity = G_LOGGER.VERBOSE

class TestCompilers(object):
    @classmethod
    def setup_class(cls):
        G_LOGGER.verbose(f"Creating build directory: {PATHS['build']}")
        os.mkdir(PATHS["build"])

    @classmethod
    def teardown_class(cls):
        G_LOGGER.verbose(f"Removing build directory: {PATHS['build']}")
        shutil.rmtree(PATHS["build"])

    @staticmethod
    def compile(compiler, input_path: str, include_dirs: List[str]=[], flags: BuildFlags=None):
        flags = flags or BuildFlags().O(3).std(17).march("native").fpic()
        include_dirs = include_dirs or [PATHS["include"], PATHS["test"]]
        # Get output path
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(PATHS["build"], f"{base}.o")
        # Generate the command needed
        cmd = compiler.compile(input_path, output_path, include_dirs, flags)
        G_LOGGER.verbose(f"Running command: {cmd}")
        subprocess.run(cmd)
        return output_path

    @pytest.mark.parametrize("compiler", [compiler.gcc, compiler.clang])
    @pytest.mark.parametrize("src_path", [PATHS["fibonacci.cpp"], PATHS["factorial.cpp"]])
    def test_can_compile(self, compiler, src_path):
        output_path = TestCompilers.compile(compiler, src_path)
        assert os.path.exists(output_path)

class TestLinkers(TestCompilers):
    @staticmethod
    def link(linker, input_paths, output_name, lib_dirs: List[str]=[], flags: BuildFlags=None, shared=False):
        flags = flags or BuildFlags().O(3).std(17).march("native").fpic()
        # Get output path
        output_path = os.path.join(PATHS["build"], output_name)
        # Generate the command needed
        cmd = linker.link(input_paths, output_path, lib_dirs, flags, shared)
        G_LOGGER.verbose(f"Running command: {cmd}")
        subprocess.run(cmd)
        return output_path

    @staticmethod
    def build_libtest(compiler, linker):
        fibonacci = TestLinkers.compile(compiler, PATHS["fibonacci.cpp"])
        factorial = TestLinkers.compile(compiler, PATHS["factorial.cpp"])
        return TestLinkers.link(linker, [fibonacci, factorial, "-lstdc++"], "libtest.so", shared=True)

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
