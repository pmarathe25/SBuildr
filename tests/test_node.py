import unittest
import sbuild.graph.node as node

# A dummy node that sets one of its attributes to True when execute is called.
class DummyNode(node.Node):
    def __init__(self, timestamp, inputs=[], name=""):
        super().__init__(timestamp, inputs, name)
        self.updated = False

    def execute(self):
        # Set this node to be as new as the newest input + 1.
        self.timestamp = max([inp.timestamp for inp in self.inputs]) + 1
        self.updated = True

class TestNodes(unittest.TestCase):
    def linear_graph(self):
        # Constructs a linear graph:
        # A -> B -> C
        A = DummyNode(0, name="A")
        B = DummyNode(0, inputs=set([A]), name="B")
        C = DummyNode(0, inputs=set([B]), name="C")
        return A, B, C

    def test_linear_outputs_correct(self):
        A, B, C = self.linear_graph()
        self.assertTrue(B in A.outputs)
        self.assertTrue(C in B.outputs)

    def test_linear_one_hop_updates(self):
        # Set A to be newer than B and check that C updates
        A, B, C = self.linear_graph()
        A.timestamp = B.timestamp + 1
        self.assertFalse(C.updated)
        C.build()
        self.assertTrue(C.updated)

    def diamond_graph(self):
        # Constructs a diamond shaped graph:
        #    B
        #   /  \
        # A     D (output)
        #   \  /
        #    C
        A = DummyNode(0, name="A")
        B = DummyNode(0, inputs=set([A]), name="B")
        C = DummyNode(0, inputs=set([A]), name="C")
        D = DummyNode(0, inputs=set([B, C]), name="D")
        return A, B, C, D

    def test_diamond_one_hop_updates(self):
        # Tests a diamond shaped graph where A is newer than B and C
        A, B, C, D = self.diamond_graph()
        A.timestamp = B.timestamp + C.timestamp + 1
        self.assertFalse(D.updated)
        D.build()
        self.assertTrue(D.updated)
