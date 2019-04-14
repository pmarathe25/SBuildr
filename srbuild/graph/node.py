from srbuild.tools import compiler, linker
from srbuild.tools.flags import BuildFlags
from srbuild.logger import G_LOGGER
from typing import List
import os

# Represents a node in a dependency graph that tracks a path on the filesystem.
class Node(object):
    def __init__(self, path: str, inputs: List["Node"]=[], cmds: List[List[str]]=[], name=""):
        self.path = path
        self.name = name or os.path.basename(path)
        self.inputs: List[Node] = []
        self.cmds = cmds
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
