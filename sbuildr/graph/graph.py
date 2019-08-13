from sbuildr.graph.node import Node
from sbuildr.logger import G_LOGGER
from typing import List, Dict, Set, Union
import copy

class Graph(dict):
    def __init__(self, nodes: Set[Node]=set()):
        self.update({node.path: node for node in nodes})

    # Whether the graph contains this node.
    def __contains__(self, val: Union[Node, str]) -> bool:
        path = val.path if isinstance(val, Node) else val
        return dict.__contains__(self, path)

    # TODO: This may need additional logic for overriding
    def __iadd__(self, other: "Graph"):
        self.update(other)
        return self

    def __add__(self, other: "Graph"):
        temp = copy.deepcopy(self)
        temp += other
        return temp

    # Adds a node if it is not already present.
    # If the path is present already, but the node is of a different type, it is overwritten.
    def add(self, node: Node) -> Node:
        if node not in self:
            G_LOGGER.verbose(f"Adding {node} under path: {node.path}")
            self[node.path] = node
        return self[node.path]

    # Returns layers of the topologically sorted graph. The first element of the list is the the
    # set of input nodes, the last element, the output nodes.
    # Note that this will exclude any nodes that are not in this graph, even if they are inputs/outputs
    # to nodes that are in the graph.
    def layers(self) -> List[Set[Node]]:
        outputs = set([node for node in self.values() if not node.outputs])
        # The layers of the graph.
        graph_layers: List[Set[Node]] = []
        graph_layers.append(outputs)
        for layer in graph_layers:
            layer_inputs = set()
            [layer_inputs.update([inp for inp in node.inputs if inp.path in self]) for node in layer]
            # [layer_inputs.update(node.inputs) for node in layer]
            if layer_inputs:
                graph_layers.append(layer_inputs)
        # Sort in order from inputs to outputs and ensure uniqueness across
        # graph_layers by removing all nodes that we've seen already.
        seen_nodes = set()
        unique_layers = []
        for layer in reversed(graph_layers):
            layer -= seen_nodes
            if layer:
                unique_layers.append(layer)
            seen_nodes.update(layer)
        return unique_layers
