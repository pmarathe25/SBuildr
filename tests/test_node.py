import unittest
import srbuild.graph.node as node

# A dummy node that sets one of its attributes to True when execute is called.
class DummyNode(node.Node):
    def __init__(self, inputs=[], name=""):
        super().__init__(inputs=inputs, name=name)
        self.updated = False

    def execute(self):
        self.updated = True
        super().execute()

class TestNodes(unittest.TestCase):
    def linear_graph(self):
        # Constructs a linear graph:
        # A -> B -> C
        A = DummyNode(name="A")
        B = DummyNode(inputs=[A], name="B")
        C = DummyNode(inputs=[B], name="C")
        return A, B, C

    def test_linear_outputs_correct(self):
        A, B, C = self.linear_graph()
        self.assertTrue(B in A.outputs)
        self.assertTrue(C in B.outputs)

    def diamond_graph(self):
        # Constructs a diamond shaped graph:
        #     A
        #   /  \
        # B     C
        #   \  /
        #    D (output)
        A = DummyNode(name="A")
        B = DummyNode(inputs=[A], name="B")
        C = DummyNode(inputs=[A], name="C")
        D = DummyNode(inputs=[B, C], name="D")
        return A, B, C, D

    def test_diamond_outputs_correct(self):
        # Tests a diamond shaped graph where A is newer than B and C
        A, B, C, D = self.diamond_graph()
        self.assertTrue(A in B.outputs)
        self.assertTrue(A in C.outputs)
        self.assertTrue([B, C] in D.outputs)
