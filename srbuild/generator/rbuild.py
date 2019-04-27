from srbuild.generator.generator import Generator
from srbuild.project.project import Project
from srbuild.graph.node import LinkedNode
from srbuild.project.target import ProjectTarget
from srbuild.graph.graph import Graph
from srbuild.logger import G_LOGGER

from typing import List, Dict
import subprocess
import time
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

    def build(self, targets: List[ProjectTarget], profiles: List[str]=[]) -> subprocess.CompletedProcess:
        paths = []
        profiles = profiles or self.project.profiles.keys()
        for profile in profiles:
            if profile not in self.project.profiles:
                G_LOGGER.critical(f"Profile {profile} does not exist in the project. Available profiles: {list(self.project.profiles.keys())}")
            # Make the required build directories first.
            build_dir = self.project.profile(profile).build_dir
            G_LOGGER.debug(f"For profile: {profile}, creating build directory: {build_dir}")
            self.project.files.mkdir(build_dir)
            for target in targets:
                if profile in target:
                    path = target[profile].path
                    G_LOGGER.verbose(f"For target: {target}, profile: {profile}, found path: {path}")
                    paths.append(path)
                else:
                    G_LOGGER.debug(f"Skipping target: {target.name} for profile: {profile}, as it does not exist.")

        # Finally, build.
        cmd = ["rbuild", f"{self.config_path}"] + paths + ["-c", self.cache_path]
        G_LOGGER.verbose(f"Build command: {' '.join(cmd)}\nTarget file paths: {paths}")
        start = time.time()
        status = subprocess.run(cmd, capture_output=True)
        end = time.time()
        if not status.returncode:
            G_LOGGER.info(f"Built {len(targets)} targets for {len(profiles)} profiles in {end - start} seconds.")
        return status
