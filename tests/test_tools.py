from sbuild.tools import compiler, linker
from sbuild.logger import G_LOGGER
import unittest
import shutil
import os
import subprocess

TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))
TEST_PROJECT_ROOT = os.path.join(TESTS_ROOT, "minimal_project")
TEST_PROJECT_BUILD = os.path.join(TEST_PROJECT_ROOT, "build")
G_LOGGER.severity = G_LOGGER.VERBOSE

class TestCompilers(unittest.TestCase):
    def setUp(self):
        self.include_dirs = set([os.path.join(TEST_PROJECT_ROOT, "include")])
        os.mkdir(TEST_PROJECT_BUILD)
        os.makedirs(os.path.join(TEST_PROJECT_BUILD, "objs"), exist_ok=True)
        os.makedirs(os.path.join(TEST_PROJECT_BUILD, "libs"), exist_ok=True)

    def compile_src(self, filename, compiler):
        input_file = os.path.join(TEST_PROJECT_ROOT, "src", f"{filename}.cpp")
        output_file = os.path.join(TEST_PROJECT_BUILD, "objs", f"{filename}.o")
        compiler.compile(input_file, output_file, include_dirs=self.include_dirs, opts=set(["--std=c++17"]))
        return output_file

    def compile_test(self, filename, compiler):
        input_file = os.path.join(TEST_PROJECT_ROOT, "test", f"{filename}.cpp")
        output_file = os.path.join(TEST_PROJECT_BUILD, "objs", f"{filename}.o")
        compiler.compile(input_file, output_file, include_dirs=self.include_dirs, opts=set(["--std=c++17"]))
        return output_file

    compilers = [compiler.gcc, compiler.clang]

    def test_can_compile_gcc(self):
        for comp in TestCompilers.compilers:
            with self.subTest():
                self.assertTrue(os.path.exists(self.compile_src("factorial", comp)))
                self.assertTrue(os.path.exists(self.compile_src("fibonacci", comp)))

    linkers = [linker.gcc, linker.clang]

    def test_can_compile_and_link_so(self):
        for comp in TestCompilers.compilers:
            with self.subTest():
                input_files = set([self.compile_src("factorial", comp), self.compile_src("fibonacci", comp)])

        for link in TestCompilers.linkers:
            with self.subTest():
                out_so = os.path.join(TEST_PROJECT_BUILD, "libs", "libmath.so")
                link.link(input_files, out_so, opts=set(["--std=c++17"]), shared=True)
                self.assertTrue(os.path.exists(out_so))

    def test_can_compile_and_link_executable(self):
        for comp in TestCompilers.compilers:
            with self.subTest():
                input_files = set([self.compile_src("factorial", comp), self.compile_src("fibonacci", comp), self.compile_test("test", comp)])

        for link in TestCompilers.linkers:
            with self.subTest():
                out_exec = os.path.join(TEST_PROJECT_BUILD, "libs", "test")
                link.link(input_files, out_exec, opts=set(["--std=c++17"]))
                self.assertTrue(os.path.exists(out_exec))
                subprocess.run([out_exec], check=True, capture_output=True)

    def tearDown(self):
        shutil.rmtree(TEST_PROJECT_BUILD)
