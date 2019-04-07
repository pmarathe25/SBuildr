from srbuild.logger import G_LOGGER
import srbuild.utils as utils
from typing import List
import time
import os

# Forward declaration for type annotations.
class Node:
    pass

class Node(object):
    def __init__(self, inputs: List[Node]=[], name=""):
        """
        Represents a node in a dependency graph.

        Optional Args:
            inputs (List[Node]): The inputs to this node.
            name (str): The name of this node.

        Vars:
            inputs (List[Node]): The inputs to this node.
            outputs (List[Node]): The outputs of this node.
            name (str): The name of this node.
        """
        self.inputs: List[Node] = []
        self.outputs: List[Node] = []
        self.name = name
        G_LOGGER.debug(f"Constructing {self} with {len(inputs)} inputs: {inputs}")
        for inp in inputs:
            self.add_input(inp)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self} (at {hex(id(self))})"

    def dependency_graph_str(self, tab_depth=0):
        """
        Returns a string representation of the dependency graph for this node.
        """
        tab = '\t'
        out = f"{tab * tab_depth}{self.name}\n"
        for inp in self.inputs:
            out += f"{inp.dependency_graph_str(tab_depth + 1)}\n"
        return out

    def add_input(self, node: Node):
        """
        Adds an input to this node and updates the `outputs` value of the input.
        """
        G_LOGGER.verbose(f"Adding {self} as an output of {node}")
        node.outputs.append(self)
        self.inputs.append(node)

    def execute(self):
        """
        This function should put the node in a state where its outputs can then be executed.
        """
        G_LOGGER.debug(f"{self}: Executing...")

class PathNode(Node):
    def __init__(self, path: str, inputs: List[Node]=[]):
        """
        A special kind of node that tracks a path on the system.

        Args:
            path (str): The path this node should track.

        Optional Args:
            inputs (List[Node]): The inputs to this node.
            name (str): The name of this node. Defaults to the basename of the path.

        Vars:
            inputs (List[Node]): The inputs to this node.
            outputs (List[Node]): The outputs of this node.
            name (str): The name of this node.
        """
        super().__init__(inputs, os.path.basename(path))
        self.path = path
