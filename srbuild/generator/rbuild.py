from srbuild.generator.generator import Generator
from srbuild.project.project import Project
from srbuild.graph.node import LinkedNode
from srbuild.graph.graph import Graph
from srbuild.logger import G_LOGGER

from typing import List
import os

class RBuildGenerator(Generator):
    def generate(self, project: Project) -> str:
        def config_for_graph(graph: Graph) -> str:
            config_file = f""
            for layer in graph.layers():
                for node in layer:
                    config_file += f"path {node.path}\n"
                    for dep in node.inputs:
                        config_file += f"dep {dep.path}\n"
                    cmd = self._node_command(node)
                    if cmd:
                        config_file += f"run {cmd[0]}\n"
                        for arg in cmd[1:]:
                            config_file += f"arg {arg}\n"
            return config_file

        if not project.configured:
            G_LOGGER.critical(f"RBuildGenerator was called with project: {project}, but it has not yet been configured for build. Have you run project.configure()?")

        # First generate the targets in the file manager, then the profiles.
        # This will ensure that ordering is correct, since the targets in profiles depend
        # on the targets in the file manager.
        config_file = config_for_graph(project.files.graph)
        for profile in project.profiles.values():
            config_file += config_for_graph(profile.graph)
        return config_file

    def build_command(self, config_path: str, targets: List[LinkedNode]) -> List[str]:
        # The cache should be adjacent to the config path
        config_basename = os.path.basename(config_path)
        cache_path = os.path.join(os.path.dirname(config_path), f"{config_basename}.cache")
        return ["rbuild", f"{config_path}"] + [target.path for target in targets] + ["-c", cache_path]
