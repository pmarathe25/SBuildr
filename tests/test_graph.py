from srbuild.graph.graph import Graph
from srbuild.graph.node import Node
from test_node import diamond_graph

def multitier_graph():
    #   A
    #  / \
    # B  |
    #  \ |
    #   C
    A = Node("A")
    B = Node("B", [A])
    C = Node("C", [A, B])
    return A, B, C

class TestGraph(object):
    def test_finalize(self):
        graph = Graph(diamond_graph())
        layers = graph.layers()
        assert len(layers) == 3
        assert len(layers[0]) == 1
        assert len(layers[1]) == 2
        assert len(layers[2]) == 1

    def test_unique_across_layers(self):
        graph = Graph(multitier_graph())
        layers = graph.layers()
        assert len(layers) == 3
        assert all([len(layer) == 1 for layer in layers])
        # Test get functionality
        assert graph["C"].path == "C"
