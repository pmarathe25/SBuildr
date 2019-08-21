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

    def configure(self, build_graph: Graph):
        config = ""

        node_ids = {}
        id = 0
        for layer in build_graph.layers():
            for node in layer:
                node_ids[node] = id
                config += f"path {node.timestamp_path()} #{id}\n"
                id += 1
                # For dependencies, we need to convert to node_ids
                if node.inputs:
                    config += f"deps {' '.join([str(node_ids[node]) for node in node.inputs])}\n"

                for cmd in node.commands():
                    config += "run"
                    for arg in cmd:
                        config += f' "{arg}"'
                    config += '\n'

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
