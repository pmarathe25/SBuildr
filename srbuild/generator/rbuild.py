from srbuild.generator.generator import Generator
from srbuild.graph.graph import Graph

class RBuildGenerator(Generator):
    # TODO(1): This should take a set of profiles and a FileManager.
    def generate(self, graph: Graph) -> str:
        config_file = f""
        for layer in graph.layers():
            for node in layer:
                config_file += f"path {node.path}\n"
                for dep in node.inputs:
                    config_file += f"dep {dep.path}\n"
                cmd = self._build_command(node)
                if cmd:
                    config_file += f"run {cmd[0]}\n"
                    for arg in cmd[1:]:
                        config_file += f"arg {arg}\n"
        return config_file
