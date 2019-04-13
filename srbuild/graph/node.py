from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from srbuild.logger import G_LOGGER
from typing import List
import os

class Node(object):
    def __init__(self, path: str, inputs: List["Node"]=[], name=""):
        """
        Represents a node in a dependency graph that tracks a path on the filesystem.

        Optional Args:
            path (str): The path this node should track.
            inputs (List[Node]): The inputs to this node.
            name (str): The name of this node.

        Vars:
            path (str): The path this node should track.
            inputs (List[Node]): The inputs to this node.
            outputs (List[Node]): The outputs of this node.
            name (str): The name of this node.
        """
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

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return hash(self) == hash(other)

class SourceNode(Node):
    def __init__(self, path: str, inputs: List["SourceNode"]=[], include_dirs: List[str]=[], name=""):
        super().__init__(path, inputs, name)
        # All include directories required for this file.
        self.include_dirs = include_dirs

class CompiledNode(Node):
    def __init__(self, path: str, inputs: List[SourceNode], compiler: compiler.Compiler, include_dirs: List[str]=[], flags: BuildFlags=BuildFlags(), name=""):
        super().__init__(path, inputs, name)
        self.compiler = compiler
        # All include directories required for this file.
        self.include_dirs = include_dirs
        G_LOGGER.debug(f"For {path}, using directories: {self.include_dirs}")
        self.flags = flags

    def add_input(self, node: SourceNode):
        if len(self.inputs) > 0:
            raise ValueError("CompiledNodes can only have a single SourceNode as an input.")
        return super().add_input(node)

class LinkedNode(Node):
    def __init__(self, path: str, inputs: List[CompiledNode], linker: linker.Linker, flags: BuildFlags=BuildFlags(), name=""):
        super().__init__(path, inputs, name)
        self.linker = linker
        self.flags = flags
