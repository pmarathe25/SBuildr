from sbuildr.tools import compiler, linker
from sbuildr.tools.flags import BuildFlags
from sbuildr.logger import G_LOGGER

from typing import List
import os

# Represents a node in a dependency graph that tracks a path on the filesystem.
class Node(object):
    def __init__(self, path: str, inputs: List["Node"]=[], name=""):
        self.path = path
        self.name = name or os.path.basename(path)
        self.inputs: List[Node] = []
        self.outputs: List[Node] = []
        G_LOGGER.debug(f"Constructing {self} with {len(inputs)} inputs: {inputs}")
        for inp in inputs:
            self.add_input(inp)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self} (at {hex(id(self))})"

    # Returns a string representation of the dependency graph for this node.
    def dependency_graph_str(self, tab_depth=0):
        tab = '\t'
        out = f"{tab * tab_depth}{self.name}\n"
        for inp in self.inputs:
            out += f"{inp.dependency_graph_str(tab_depth + 1)}\n"
        return out

    def add_input(self, node: "Node"):
        G_LOGGER.verbose(f"Adding {self} as an output of {node}")
        node.outputs.append(self)
        self.inputs.append(node)

class SourceNode(Node):
    def __init__(self, path: str, inputs: List["SourceNode"]=[], include_dirs: List[str]=None, name=""):
        super().__init__(path, inputs, name)
        # All include directories required for this file.
        self.include_dirs = include_dirs

class CompiledNode(Node):
    # These include_dirs are user-specified, since any scanned dirs would be in the SourceNode.
    def __init__(self, path: str, input: SourceNode, compiler: compiler.Compiler, include_dirs: List[str]=[], flags: BuildFlags=BuildFlags(), name=""):
        super().__init__(path, [input], name)
        self.compiler = compiler
        # All include directories required for this file.
        self.include_dirs = include_dirs
        self.flags = flags

    def add_input(self, node: SourceNode):
        if len(self.inputs) > 0:
            G_LOGGER.critical(f"Cannot create a CompiledNode with more than one source. This node already has one input: {self.inputs}")
        super().add_input(node)

# In LinkedNodes, the name field contains the user friendly name (i.e. without linker signature)
class LinkedNode(Node):
    def __init__(self, path: str, inputs: List[Node], linker: linker.Linker, libs: List[str]=[], lib_dirs: List[str]=[], flags: BuildFlags=BuildFlags(), name=""):
        super().__init__(path, inputs, name)
        self.linker = linker
        self.libs = libs
        self.lib_dirs = lib_dirs
        self.flags = flags
