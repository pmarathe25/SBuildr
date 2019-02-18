from typing import Set
from sbuild.logger import G_LOGGER

# Forward declaration for type annotations.
class Node:
    pass

class Node(object):
    def __init__(self, timestamp: int, inputs: Set[Node]=[], name=""):
        """
        Represents a node in a dependency graph.

        Args:
            timestamp (int): The timestamp for this node (generally in nanoseconds since epoch).

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

    def needs_update(self):
        """
        Whether this node is out of date compared to its inputs.

        Returns True if an input is newer than this node. Note that if inputs are out of date as well, this function will NOT perform recursive checks.

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
        Calls build recursively on all input nodes, then executes this node if an update is required.
        """
        for inp in self.inputs:
            inp.build()

        if self.needs_update():
            G_LOGGER.debug(f"{self} out of date, executing.")
            self.execute()

    def execute(self):
        """
        Unconditionally execute this node and update its timestamp accordingly.
        """
        pass
