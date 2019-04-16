from srbuild.graph.node import Node
from typing import List, Dict, Set

class Graph(set):
    def __init__(self, nodes: Set[Node]={}):
        self.nodes: Dict[str, Node] = {node.path: node for node in nodes}

    # Adds a node if it is not already present.
    def add(self, node: Node) -> Node:
        if node.path not in self.nodes:
            self.nodes[node.path] = node
        return self.nodes[node.path]

    def __getitem__(self, path: str) -> Node:
        return self.nodes[path]

    # Indicates that the graph is completely populated.
    def layers(self) -> List[Set[Node]]:
        outputs = set([node for node in self.nodes.values() if not node.outputs])
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
