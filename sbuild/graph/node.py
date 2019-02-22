from sbuild.logger import G_LOGGER
import sbuild.utils as utils
from typing import Set, List
import os

# Forward declaration for type annotations.
class Node:
    pass

class Node(object):
    def __init__(self, timestamp: int=0, inputs: Set[Node]=[], name=""):
        """
        Represents a node in a dependency graph.

        Optional Args:
            inputs (Set[Node]): The inputs to this node.
            name (str): The name of this node. Defaults to Node {num_nodes} where num_nodes is the total number of nodes that have been constructed so far.

        Vars:
            timestamp (int): The timestamp for this node (generally in nanoseconds since epoch).
            inputs (Set[Node]): The inputs to this node.
            outputs (Set[Node]): The outputs of this node.
            name (str): The name of this node.
        """
        self.timestamp = timestamp
        self.inputs = set()
        self.outputs = set()
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
        Adds an input to this node. Each node is responsible for updating the `outputs` value of its inputs.
        """
        G_LOGGER.verbose(f"Adding {self} as an output of {node}")
        node.outputs.add(self)
        self.inputs.add(node)

    def needs_update(self) -> bool:
        """
        Determines whether this node is out of date compared to its inputs.

        Returns True if an input is newer than this node. This function will NOT perform recursive checks.

        Returns:
            bool: Whether this node needs to be updated.
        """
        for inp in self.inputs:
            if self.timestamp < inp.timestamp:
                G_LOGGER.verbose(f"{self} needs update as input {inp} is newer.")
                return True
        return False

    def build(self):
        """
        Calls build recursively on all input nodes, then executes this node if an update is required as per `needs_update`.

        Returns:
            bool: Whether the node was executed.
        """
        for inp in self.inputs:
            inp.build()

        self.update()

    def update(self):
        """
        Executes this node, but only if an update is required, as indicated by `self.needs_update()`
        """
        if self.needs_update():
            self.execute()
            return True
        return False

    def execute(self):
        """
        This function should put the node in a state where its outputs can then be executed.

        This function is also responsible for updating the timestamp and multiple consecutive executions should work as expected.
        """
        G_LOGGER.debug(f"{self}: Executing...")
        # Set this node to be as new as it's newest input.
        self.timestamp = max([inp.timestamp for inp in self.inputs] + [self.timestamp])

    def clean(self):
        """
        This function should undo any changes made by execute.
        """
        G_LOGGER.debug(f"{self}: Cleaning...")

class PathNode(Node):
    def __init__(self, path: str, inputs: Set[Node]):
        """
        A special kind of node that tracks a path on the system.

        Args:
            path (str): The path this node should track. Timestamp information is derived from this path.

        Optional Args:
            inputs (Set[Node]): The inputs to this node.
            name (str): The name of this node. Defaults to Node {num_nodes} where num_nodes is the total number of nodes that have been constructed so far.

        Vars:
            timestamp (int): The timestamp for this node (generally in nanoseconds since epoch).
            inputs (Set[Node]): The inputs to this node.
            outputs (Set[Node]): The outputs of this node.
            name (str): The name of this node.
        """
        super().__init__(utils.timestamp(path), inputs, os.path.basename(path))
        self.path = path
