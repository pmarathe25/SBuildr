from srbuild.graph.node import Node

class TestNodes(object):
    def linear_graph(self):
        # Constructs a linear graph:
        # A -> B -> C
        A = Node(name="A")
        B = Node(inputs=[A], name="B")
        C = Node(inputs=[B], name="C")
        return A, B, C

    def test_linear_outputs_correct(self):
        A, B, C = self.linear_graph()
        assert B in A.outputs
        assert C in B.outputs

    def diamond_graph(self):
        # Constructs a diamond shaped graph:
        #     A
        #   /  \
        # B     C
        #   \  /
        #    D (output)
        A = Node(name="A")
        B = Node(inputs=[A], name="B")
        C = Node(inputs=[A], name="C")
        D = Node(inputs=[B, C], name="D")
        return A, B, C, D

    def test_diamond_outputs_correct(self):
        A, B, C, D = self.diamond_graph()
        assert B in A.outputs and C in A.outputs
        assert D in B.outputs
        assert D in C.outputs
