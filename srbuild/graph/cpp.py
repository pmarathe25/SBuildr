from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from srbuild.graph.node import PathNode
from srbuild.logger import G_LOGGER
from typing import List

class SourceNode(PathNode):
    def __init__(self, path: str, inputs: List["SourceNode"]=[], include_dirs: List[str]=[]):
        """
        A specialization of PathNode that tracks include directories required for a source file.
        """
        super().__init__(path, inputs)
        # All include directories required for this file.
        self.include_dirs = include_dirs
        G_LOGGER.debug(f"For {path}, using directories: {self.include_dirs}")

class ObjectNode(PathNode):
    def __init__(self, path: str, inputs: List[SourceNode], compiler: compiler.Compiler, flags: BuildFlags=BuildFlags()):
        if len(inputs) > 1:
            raise ValueError("ObjectNodes can only have a single SourceNode as an input.")
        super().__init__(path, inputs)
        self.compiler = compiler
        self.flags = flags

    def add_input(self, node: SourceNode):
        if len(self.inputs) > 0:
            raise ValueError("ObjectNodes can only have a single SourceNode as an input.")
        return super().add_input(node)


class DynamicLibraryNode(PathNode):
    def __init__(self, path: str, inputs: List[ObjectNode], linker: linker.Linker, flags: BuildFlags=BuildFlags()):
        super().__init__(path, inputs)
        self.linker = linker
        self.flags = flags
