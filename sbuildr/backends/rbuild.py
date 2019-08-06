from sbuildr.backends.backend import Backend
from sbuildr.graph.graph import Graph
from sbuildr.graph.node import Node
from sbuildr.logger import G_LOGGER
from sbuildr.misc import utils

from typing import List, Dict
import subprocess
import time
import os

class RBuildBackend(Backend):
    CONFIG_FILENAME = "rbuild"

    def __init__(self, build_dir: str):
        super().__init__(build_dir)
        self.config_file = os.path.join(self.build_dir, RBuildBackend.CONFIG_FILENAME)

    def configure(self, source_graph: Graph, profile_graphs: List[Graph]):
        # Map each node to it's integer id. This is unique per rbuild file.
        node_ids = {}
        id = 0

        def config_for_graph(graph: Graph) -> str:
            nonlocal node_ids, id
            config_file = f""
            for layer in graph.layers():
                for node in layer:
                    node_ids[node] = id
                    config_file += f"path {node.path} #{id}\n"
                    id += 1
                    # For dependencies, we need to convert to node_ids
                    if node.inputs:
                        config_file += f"deps {' '.join([str(node_ids[node]) for node in node.inputs])}\n"
                    cmd = self._node_command(node)
                    if cmd:
                        config_file += "run"
                        for arg in cmd:
                            config_file += f' "{arg}"'
                        config_file += '\n'
            return config_file

        # First generate the targets in the file manager, then the profiles.
        # This will ensure that ordering is correct, since the targets in profiles depend
        # on the targets in the file manager.
        config = config_for_graph(source_graph)
        for profile_graph in profile_graphs:
            config += config_for_graph(profile_graph)

        G_LOGGER.info(f"Generating configuration files in build directory: {self.build_dir}")
        with open(self.config_file, "w") as f:
            G_LOGGER.debug(f"Writing {self.config_file}")
            f.write(config)

    def build(self, nodes: List[Node]) -> (subprocess.CompletedProcess, float):
        # Early exit if no targets were provided
        if not nodes:
            G_LOGGER.debug(f"No targets specified, skipping build.")
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"No targets specified"), 0

        paths = [node.path for node in nodes]
        cmd = ["rbuild", f"{self.config_file}"] + paths
        G_LOGGER.verbose(f"Build command: {' '.join(cmd)}\nTarget file paths: {paths}")
        return utils.time_subprocess(cmd)
