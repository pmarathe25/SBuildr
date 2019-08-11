from sbuildr.project.dependencies.builders.builder import DependencyBuilder
from sbuildr.misc import utils
from sbuildr.logger import G_LOGGER
import subprocess
import sys

class SBuildrBuilder(DependencyBuilder):
    def __init__(self, build_script_name: str="build.py"):
        """
        Builds projects using the SBuildr build system.

        :param build_script_name: The name of the build script. Defaults to "build.py".
        """
        self.build_script_name = build_script_name

    def install(self, source_dir: str, header_dir: str, lib_dir: str, exec_dir: str):
        # Configure, then install the project.
        configure_status = subprocess.run([sys.executable, self.build_script_name, "configure"], capture_output=True, cwd=source_dir)
        if configure_status.returncode:
            G_LOGGER.critical(f"Failed to configure dependency in {source_dir} with:\n{utils.subprocess_output(configure_status)}")
        project_status = subprocess.run([sys.executable, self.build_script_name], capture_output=True, cwd=source_dir)
        if project_status.returncode:
            G_LOGGER.critical(f"Could not run project build configuration script: {self.build_script_name}")
        install_status = subprocess.run(["sbuildr", "install", "-I", header_dir, "-L", lib_dir, "-X", exec_dir, "-f"], capture_output=True, cwd=source_dir)
        if install_status.returncode:
            G_LOGGER.critical(f"Failed to install dependency from {source_dir} with:\n{utils.subprocess_output(install_status)}")
