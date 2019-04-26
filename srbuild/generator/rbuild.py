from srbuild.generator.generator import Generator
from srbuild.project.project import Project
from srbuild.graph.node import LinkedNode
from srbuild.graph.graph import Graph
from srbuild.logger import G_LOGGER

from typing import List, Dict
import subprocess
import os

class RBuildGenerator(Generator):
    CONFIG_FILENAME = "rbuild"
    CACHE_FILENAME = f"{CONFIG_FILENAME}.cache"

    def __init__(self, project: Project):
        super().__init__(project)
        # The cache should be adjacent to the config path
        self.config_path = os.path.join(self.project.files.build_dir, RBuildGenerator.CONFIG_FILENAME)
        self.cache_path = os.path.join(self.project.files.build_dir, RBuildGenerator.CACHE_FILENAME)

    def generate(self):
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

        self.project.prepare_for_build()
        # First generate the targets in the file manager, then the profiles.
        # This will ensure that ordering is correct, since the targets in profiles depend
        # on the targets in the file manager.
        config = config_for_graph(self.project.files.graph)
        for profile in self.project.profiles.values():
            config += config_for_graph(profile.graph)

        self.project.files.mkdir(self.project.files.build_dir)
        with open(self.config_path, "w") as f:
            f.write(config)

    # TODO(1): Change LinkedNode to Target instead so we can always pick the correct profile.
    def build(self, targets: Dict[str, List[LinkedNode]]) -> subprocess.CompletedProcess:
        all_nodes = []
        for profile_name, nodes in targets.items():
            profile = self.project.profiles[profile_name]
            # Make the required build directories first.
            self.project.files.mkdir(profile.build_dir)
            for node in nodes:
                if node not in profile.graph:
                    G_LOGGER.critical(f"Node {node} was specified for {profile_name}, but it does not exist in this profile. Is it in another profile?")
                all_nodes.append(node)

        # Finally, build
        cmd = ["rbuild", f"{self.config_path}"] + [node.path for node in all_nodes] + ["-c", self.cache_path]
        return subprocess.run(cmd, capture_output=True)
