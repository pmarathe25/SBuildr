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

        if self.needs_update():
            G_LOGGER.debug(f"{self} out of date, executing.")
            self.execute()
            return True
        return False

    def execute(self):
        """
        Unconditionally execute this node and update its timestamp accordingly.
        """
        # Set this node to be as new as it's newest input.
        # Or, if it is already newer than its inputs, leave it unchanged.
        self.timestamp = max([inp.timestamp for inp in self.inputs] + [self.timestamp])

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
        self.path = path
        super().__init__(utils.timestamp(self.path), inputs, os.path.basename(self.path))

    def execute(self):
        """
        Updates this node's timestamp based on the path being tracked, then calls Node's `execute` function.
        Effectively, this means that the timestamp of this node will be the maximum of the tracked path's timestamp
        and the timestamps of the input nodes.
        """
        self.timestamp = utils.timestamp(self.path)
        super().execute()
