from srbuild.graph.node import LinkedNode
from typing import NewType, Dict

# A Dict[str, LinkedNode] that maps profile names to the LinkedNodes for a target
class ProjectTarget(dict):
    def __init__(self, name, is_lib=False, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.name = name
        self.is_lib = is_lib
