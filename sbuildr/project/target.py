from sbuildr.dependencies.dependency import Dependency
from sbuildr.logger import G_LOGGER
from typing import Dict, List

import copy

# A Dict[str, LinkedNode] that maps profile names to the LinkedNodes for a target
class ProjectTarget(dict):
    def __init__(self, name, internal: bool, is_lib: bool, dependencies: List[Dependency]=[], *args, **kwargs):
        """
        Represents a single target in a project.

        Vars:
            :param name: The name of this target.
        """
        super().__init__(self, *args, **kwargs)
        self.name = name
        self.internal = internal
        self.is_lib = is_lib
        self.dependencies: List[Dependency] = copy.copy(dependencies)
        G_LOGGER.verbose(f"Created ProjectTarget: {self.name} (internal: {self.internal}), (is_lib: {self.is_lib}), with dependencies: {self.dependencies}")


    def __str__(self):
        return f"{self.name} {'(lib)' if self.is_lib else '(exe)'}"
