from sbuildr.graph.node import Node
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
            self[node.path] = node
        return self[node.path]

    def layers(self) -> List[Set[Node]]:
        outputs = set([node for node in self.values() if not node.outputs])
        # The layers of the graph.
        _layers: List[Set[Node]] = []
        _layers.append(outputs)
        for layer in _layers:
            layer_inputs = set()
            [layer_inputs.update(node.inputs) for node in layer]
            if layer_inputs:
                _layers.append(layer_inputs)
        # Sort in order from inputs to outputs and ensure uniqueness across
        # layers by removing all nodes that we've seen already.
        seen_nodes = set()
        _unique_layers = []
        for layer in reversed(_layers):
            layer -= seen_nodes
            if layer:
                _unique_layers.append(layer)
            seen_nodes.update(layer)
        return _unique_layers
