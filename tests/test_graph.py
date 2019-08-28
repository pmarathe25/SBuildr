from sbuildr.graph.graph import Graph
from sbuildr.graph.node import Node, Library

def linear_graph():
    # Constructs a linear graph:
    # A -> B -> C
    A = Node(path="A")
    B = Node(inputs=[A], path="B")
    C = Node(inputs=[B], path="C")
    return A, B, C

def diamond_graph():
    # Constructs a diamond shaped graph:
    #     A
    #   /  \
    # B     C
    #   \  /
    #    D (output)
    A = Node(path="A")
    B = Node(inputs=[A], path="B")
    C = Node(inputs=[A], path="C")
    D = Node(inputs=[B, C], path="D")
    return A, B, C, D

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
        assert layers[-1].pop().path == "C"

class TestNodes(object):
    def test_linear_outputs_correct(self):
        A, B, C = linear_graph()
        assert B in A.outputs
        assert C in B.outputs

    def test_diamond_outputs_correct(self):
        A, B, C, D = diamond_graph()
        assert B in A.outputs and C in A.outputs
        assert D in B.outputs
        assert D in C.outputs

    def test_hashes_same_node(self):
        A0 = Node(path="A")
        A1 = A0
        assert hash(A0) == hash(A1)
        test = set([A0, A1])
        assert len(test) == 1

    def test_hashes_different_node(self):
        A = Node(path="A")
        B = Node(path="B")
        assert hash(A) != hash(B)
        test = set([A, B])
        assert len(test) == 2

    def test_library_node_has_no_path(self):
        libstdcpp = Library("stdc++")
        assert not libstdcpp.path
