from sbuildr.backends.backend import Backend
from sbuildr.graph.graph import Graph
from sbuildr.graph.node import Node
from sbuildr.logger import G_LOGGER
from sbuildr.misc import utils

from typing import List, Dict
import multiprocessing
import subprocess
import time
import os

class RBuildBackend(Backend):
    CONFIG_FILENAME = "rbuild"

    def __init__(self, build_dir: str):
        super().__init__(build_dir)
        self.config_file = os.path.join(self.build_dir, RBuildBackend.CONFIG_FILENAME)

    def configure(self, build_graph: Graph):
        config = ""

        node_ids = {}
        id = 0
        for layer in build_graph.layers():
            for node in layer:
                for artifact in node.artifacts():
                    config += f"path {artifact.path} #{id}\n"

                    if artifact.dependencies:
                        config += f"deps {' '.join([str(node_ids[node]) for node in artifact.dependencies])}\n"

                    for cmd in artifact.commands:
                        config += "run"
                        for arg in cmd:
                            config += f' "{arg}"'
                        config += '\n'

                    for cmd in artifact.always:
                        config += "always"
                        for arg in cmd:
                            config += f' "{arg}"'
                        config += '\n'

                    # Only the id for the final artifact is used by other nodes
                    node_ids[node] = id
                    id += 1

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
        cmd = ["rbuild", "--threads", str(multiprocessing.cpu_count()), f"{self.config_file}"] + paths
        G_LOGGER.verbose(f"Build command: {' '.join(cmd)}\nTarget file paths: {paths}")
        return utils.time_subprocess(cmd)
