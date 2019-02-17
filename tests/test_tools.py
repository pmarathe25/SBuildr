import sbuild.tools.compiler as compiler
from sbuild.Logger import G_LOGGER
import unittest
import os

TESTS_ROOT = os.path.abspath(os.path.dirname(__file__))
TEST_PROJECT_ROOT = os.path.join(TESTS_ROOT, "minimal_project")
G_LOGGER.severity = G_LOGGER.VERBOSE

class TestCompilers(unittest.TestCase):
    def setUp(self):
        self.gcc = compiler.Compiler()
        self.include_dirs = [os.path.join(TEST_PROJECT_ROOT, "include")]

    def test_can_compile(self):
        input_file = os.path.join(TEST_PROJECT_ROOT, "src", "factorial.cpp")
        output_file = os.path.join(TEST_PROJECT_ROOT, "build", "objs", "factorial.o")
        try:
            os.remove(output_file)
        except FileNotFoundError:
            pass
        self.gcc.compile(input_file, output_file, include_dirs=self.include_dirs)
        self.assertTrue(os.path.exists(output_file))
