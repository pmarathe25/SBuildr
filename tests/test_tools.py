import sbuild.tools.compiler as compiler
import unittest
import os

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
MINIMAL_PROJECT_ROOT = os.path.join(ROOT_DIR, "tests", "minimal_project")

class TestCompilers(unittest.TestCase):
    def setUp(self):
        self.gcc = compiler.Compiler()

    def test_can_compile(self):
        input_file = os.path.join(MINIMAL_PROJECT_ROOT, "src", "factorial.cpp")
        output_file = os.path.join(MINIMAL_PROJECT_ROOT, "build", "objs", "factorial.o")
        self.gcc.compile()
