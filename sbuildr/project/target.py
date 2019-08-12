from sbuildr.project.dependencies.dependency import Dependency
from sbuildr.graph.node import LinkedNode
from typing import Dict, List

# A Dict[str, LinkedNode] that maps profile names to the LinkedNodes for a target
class ProjectTarget(dict):
    def __init__(self, name, internal: bool=False, dependencies: List[Dependency]=[], *args, **kwargs):
        """
        Represents a single target in a project.

        Vars:
            :param name: The name of this target.
        """
        super().__init__(self, *args, **kwargs)
        self.name = name
        self.internal = False
        self.is_lib = False
        self.dependencies: List[Dependency] = []

    def __str__(self):
        return f"{self.name} {'(lib)' if self.is_lib else '(exe)'}"
