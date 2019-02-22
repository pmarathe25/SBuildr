from sbuild.tools.compiler import Compiler
from sbuild.graph.node import PathNode
from sbuild.logger import G_LOGGER
import sbuild.utils as utils
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
    def __init__(self, path: str, dirs: List[str]=[], inputs: Set[SourceNode]=[]):
        """
        A specialization of PathNode that tracks the containing directories of its inputs.

        Vars:
            dirs (List[str]): A list of directories where any files included by this file can be found.
        """
        self.dirs = dirs
        # All include directories, including directories from any input nodes. This is set up by execute.
        self.include_dirs = None
        super().__init__(path, inputs)
        G_LOGGER.debug(f"For {path}, using directories: {self.dirs}")

    def needs_update(self):
        # Source nodes are out of date when they are either older than their dependencies,
        # or when include_dirs is None (to distinguish from being correctly empty).
        return self.include_dirs is None or super().needs_update()

    def execute(self):
        super().execute()
        self.include_dirs = []
        self.include_dirs.extend(self.dirs)
        G_LOGGER.verbose(f"{self}: Using dirs: {self.dirs}")
        for inp in self.inputs:
            G_LOGGER.verbose(f"{self}: For input {inp}, found dirs: {inp.include_dirs}")
            self.include_dirs.extend(inp.include_dirs)
        G_LOGGER.debug(f"{self}: include_dirs: {self.include_dirs}")
        # If the file is newer than this node's timestamp, update the timestamp.
        self.timestamp = max([self.timestamp, utils.timestamp(self.path)])
        G_LOGGER.verbose(f"{self}: Updating timestamp to {self.timestamp}")

    def clean(self):
        super().clean()
        self.include_dirs = None

class ObjectNode(PathNode):
    def __init__(self, inputs: Set[SourceNode], compiler: Compiler, output_path: str, opts: Set[str]=[]):
        assert len(inputs) <= 1, "ObjectNodes can only have a single SourceNode as an input."
        super().__init__(output_path, inputs)
        self.compiler = compiler
        self.opts = opts
        # Get the first and only input.
        self.source_node = next(iter(inputs))

    def add_input(self, node: SourceNode):
        assert len(self.inputs) == 0, "ObjectNodes can only have a single SourceNode as an input."
        return super().add_input(node)

    def execute(self):
        super().execute()
        self.compiler.compile(input_file=self.source_node.path, output_file=self.path, include_dirs=self.source_node.include_dirs, opts=self.opts)
        # For object nodes, the timestamp should always be tied to the file.
        self.timestamp = utils.timestamp(self.path)

    def clean(self):
        super().clean()
        os.remove(self.path)
