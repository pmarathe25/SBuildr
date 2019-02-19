from sbuild.tools.compiler import Compiler
from sbuild.graph.node import PathNode
from sbuild.logger import G_LOGGER
import sbuild.utils as utils
from typing import Set
import os

# Forward declaration for type annotations.
class HeaderNode:
    pass

class HeaderNode(PathNode):
    def __init__(self, path: str, inputs: Set[HeaderNode]=[]):
        """
        A specialization of PathNode that tracks its own containing directory in addition to those of its inputs.
        """
        self.dirs = set([os.path.dirname(path)])
        super().__init__(path, inputs)
        G_LOGGER.debug(f"For header {path}, using directories: {self.dirs}")

    def add_input(self, node: HeaderNode):
        self.dirs.update(node.dirs)
        super().add_input(node)

class SourceNode(PathNode):
    def __init__(self, path: str, inputs: Set[HeaderNode]=[]):
        """
        A specialization of PathNode that tracks the containing directories of its inputs.

        Vars:
            dirs (Set[str]): A set of directories of this source node's inputs. This is equivalent to the directories that should be passed as include_dirs to the compiler.
        """
        self.dirs = set()
        super().__init__(path, inputs)
        G_LOGGER.debug(f"For source {path}, using directories: {self.dirs}")

    def add_input(self, node: HeaderNode):
        self.dirs.update(node.dirs)
        super().add_input(node)

class ObjectNode(PathNode):
    def __init__(self, inputs: Set[SourceNode], compiler: Compiler, opts: Set[str]=[]):
        assert len(inputs) <= 1, "ObjectNodes can only have a single SourceNode as an input."
        self.opts = opts
        self.compiler = compiler
        # Get the first element of the set.
        self.source_node = next(iter(inputs))
        path = f"{os.path.splitext(self.source_node.path)[0]}.{compiler.signature(self.source_node.dirs, opts)}.o"
        super().__init__(path, inputs)

    def add_input(self, node: SourceNode):
        assert len(self.inputs) == 0, "ObjectNodes can only have a single SourceNode as an input."
        return super().add_input(node)

    def execute(self):
        self.compiler.compile(input_file=self.source_node.path, output_file=self.path, include_dirs=self.source_node.dirs, opts=self.opts)
        super().execute()
