from srbuild.tools import compiler, linker
from srbuild.graph.node import PathNode
from srbuild.logger import G_LOGGER
import srbuild.utils as utils
from typing import Set, List
import os

# Forward declaration for type annotations.
class SourceNode:
    pass

# TODO: dirs could be specified from a higher level instead of being the dirname of the tracked file.
# For example, if a source file includes a header using a longer path i.e. include <path/to/my/header.h>,
# then the SOURCE file should have an include dir pointing to path/to/my/../../..
# IMPORTANT: Finally, execute can be used to propagate the paths up, rather than making every node stateful.
class SourceNode(PathNode):
    def __init__(self, path: str, inputs: List[SourceNode]=[], include_dirs: List[str]=[]):
        """
        A specialization of PathNode that tracks include directories required for a source file.
        """
        # All include directories required for this file. This is set up by execute.
        super().__init__(path, inputs)
        self.include_dirs = include_dirs
        G_LOGGER.debug(f"For {path}, using directories: {self.dirs}")

    def execute(self):
        super().execute()
        # TODO: Invoke header manager here instead of doing it this way.
        for inp in self.inputs:
            G_LOGGER.verbose(f"{self}: For input {inp}, found dirs: {inp.include_dirs}")
            self.include_dirs.extend(inp.include_dirs)
        G_LOGGER.debug(f"{self}: include_dirs: {self.include_dirs}")

# TODO: opts here should instead be CompilerOptions instance.
class ObjectNode(PathNode):
    def __init__(self, inputs: List[SourceNode], compiler: compiler.Compiler, output_path: str, opts: Set[str]=[]):
        if len(inputs) > 1:
            raise ValueError("ObjectNodes can only have a single SourceNode as an input.")

        super().__init__(output_path, inputs)
        self.compiler = compiler
        self.opts = opts
        # Get the first and only input.
        self.source_node = inputs[0]

    def add_input(self, node: SourceNode):
        if len(self.inputs) > 0:
            raise ValueError("ObjectNodes can only have a single SourceNode as an input.")

        return super().add_input(node)

    # TODO: This should set up the command needed to build this object.
    def execute(self):
        super().execute()
        self.compiler.compile(input_file=self.source_node.path, output_file=self.path, include_dirs=self.source_node.include_dirs, opts=self.opts)
        # For object nodes, the timestamp should always be tied to the file.
        self.timestamp = utils.timestamp(self.path)

class DynamicLibraryNode(PathNode):
    def __init__(self, inputs: Set[ObjectNode], linker: linker.Linker, output_path: str, opts: Set[str]=[]):
        super().__init__(output_path, inputs)
        self.linker = linker
        self.opts = opts

    def execute(self):
        super().execute()
        # TODO: Figure out how to handle link dirs and external libraries.
        self.linker.link(input_files=set([inp.path for inp in self.inputs]), output_file=self.path, opts=self.opts, shared=True)
