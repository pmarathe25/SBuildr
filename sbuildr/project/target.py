from sbuildr.dependencies.dependency import DependencyLibrary
from sbuildr.graph.node import LinkedNode
from sbuildr.logger import G_LOGGER
from typing import Dict, List

# A Dict[str, LinkedNode] that maps profile names to the LinkedNodes for a target
class ProjectTarget(dict):
    def __init__(self, name, internal: bool=False, dependent_libraries: List[DependencyLibrary]=[], *args, **kwargs):
        """
        Represents a single target in a project.

        Vars:
            :param name: The name of this target.
        """
        super().__init__(self, *args, **kwargs)
        self.name = name
        self.internal = False
        self.is_lib = False
        self.dependent_libraries: List[Dependency] = dependent_libraries
        G_LOGGER.verbose(f"Created ProjectTarget: {self.name} (internal: {self.internal}), (is_lib: {self.is_lib}), with dependent libraries: {self.dependent_libraries}")


    def __str__(self):
        return f"{self.name} {'(lib)' if self.is_lib else '(exe)'}"
