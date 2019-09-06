from sbuildr.graph.node import Node
from sbuildr.logger import G_LOGGER
from typing import List, Set, Union

class Graph(set):
    def find_node_with_path(self, path: str) -> Union[Node, None]:
        for node in self:
            if node.path == path:
                return node
        return None

    def add(self, node: Node) -> Node:
        set.add(self, node)
        G_LOGGER.verbose(f"Adding {node} with path: {node.path}")
        return node

    # Returns layers of the topologically sorted graph. The first element of the list is the the
    # set of input nodes, the last element, the output nodes.
    # Note that this will exclude any nodes that are not in this graph, even if they are inputs/outputs
    # to nodes that are in the graph.
    def layers(self) -> List[Set[Node]]:
        # Graph output nodes do not have any outputs within the graph.
        def is_graph_output(node):
            return all([out not in self for out in node.outputs])

        outputs = set([node for node in self if is_graph_output(node)])
        # The layers of the graph.
        graph_layers: List[Set[Node]] = []
        graph_layers.append(outputs)
        for layer in graph_layers:
            layer_inputs = set()
            [layer_inputs.update([inp for inp in node.inputs if inp in self]) for node in layer]
            # [layer_inputs.update(node.inputs) for node in layer]
            if layer_inputs:
                graph_layers.append(layer_inputs)
        # Sort in order from inputs to outputs and ensure uniqueness across
        # graph_layers by removing all nodes that we've seen already.
        seen_nodes = set()
        unique_layers: List[Set[Node]] = []
        for layer in reversed(graph_layers):
            layer -= seen_nodes
            if layer:
                unique_layers.append(layer)
            seen_nodes.update(layer)
        return unique_layers
