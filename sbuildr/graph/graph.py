from sbuildr.graph.node import Node
from typing import List, Dict, Set

class Graph(dict):
    def __init__(self, nodes: Set[Node]=set()):
        self.update({node.path: node for node in nodes})

    # The path must exist in the graph, and the node type must be the same.
    def __contains__(self, node: Node) -> bool:
        return self.contains_path(node.path) and type(self[node.path]) == type(node)

    def contains_path(self, path: str) -> bool:
        return dict.__contains__(self, path)

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
