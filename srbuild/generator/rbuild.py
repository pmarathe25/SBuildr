from srbuild.generator.generator import Generator
from srbuild.project.target import ProjectTarget
from srbuild.logger import G_LOGGER, plural
from srbuild.project.project import Project
from srbuild.graph.node import LinkedNode
from srbuild.graph.graph import Graph

from typing import List, Dict
import subprocess
import time
import os

class RBuildGenerator(Generator):
    CONFIG_FILENAME = "rbuild"

    def __init__(self, project: Project):
        super().__init__(project)
        self.config_file = os.path.join(self.project.files.build_dir, RBuildGenerator.CONFIG_FILENAME)

    def generate(self):
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
                    # For dependecies, we need to convert to node_ids
                    if node.inputs:
                        config_file += f"deps {' '.join([str(node_ids[node]) for node in node.inputs])}\n"
                    cmd = self._node_command(node)
                    if cmd:
                        config_file += "run"
                        for arg in cmd:
                            config_file += f' "{arg}"'
                        config_file += '\n'
            return config_file

        self.project.prepare_for_build()
        # First generate the targets in the file manager, then the profiles.
        # This will ensure that ordering is correct, since the targets in profiles depend
        # on the targets in the file manager.
        config = config_for_graph(self.project.files.graph)
        for profile in self.project.profiles.values():
            config += config_for_graph(profile.graph)

        G_LOGGER.info(f"Generating configuration files in build directory: {self.project.files.build_dir}")
        self.project.files.mkdir(self.project.files.build_dir)
        with open(self.config_file, "w") as f:
            G_LOGGER.debug(f"Writing {self.config_file}")
            f.write(config)

    def needs_configure(self) -> bool:
        # The generator's build configuration file must exist and should be at least as new as the project's config file.
        if not os.path.exists(self.config_file):
            return True
        if os.path.getmtime(self.config_file) < os.path.getmtime(self.project.config_file):
            G_LOGGER.warning(f"Project configuration file ({self.project.config_file}) is newer than RBuildGenerator's configuration file ({self.config_file}). You may need to reconfigure.")
        return False

    def build(self, targets: List[ProjectTarget], profiles: List[str]=[]) -> subprocess.CompletedProcess:
        # Early exit if no targets were provided
        if not targets:
            G_LOGGER.debug(f"No targets specified, skipping build.")
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"No targets specified")

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
        cmd = ["rbuild", f"{self.config_file}"] + paths
        G_LOGGER.verbose(f"Build command: {' '.join(cmd)}\nTarget file paths: {paths}")
        # TODO: Move this into parent.
        start = time.time()
        status = subprocess.run(cmd, capture_output=True)
        end = time.time()
        if not status.returncode:
            G_LOGGER.info(f"Built {plural('target', len(targets))} for {plural('profile', len(profiles))} in {end - start} seconds.")
        return status
