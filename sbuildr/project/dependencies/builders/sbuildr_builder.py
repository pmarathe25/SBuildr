from sbuildr.project.dependencies.builders.builder import DependencyBuilder
from sbuildr.project.project import Project
from sbuildr.misc import utils
from sbuildr.logger import G_LOGGER
import subprocess
import sys
import os

class SBuildrBuilder(DependencyBuilder):
    def __init__(self, build_script_path: str="build.py", project_save_path: str=Project.DEFAULT_SAVED_PROJECT_NAME):
        f"""
        Builds projects using the SBuildr build system.

        :param build_script_path: The path to the build script, relative to the project root. Defaults to "build.py".
        :param project_save_path: The path at which the build script saves the project. Defaults to {Project.DEFAULT_SAVED_PROJECT_NAME}
        """
        self.build_script_path = build_script_path
        self.project_save_path = project_save_path

    def install(self, source_dir: str, header_dir: str, lib_dir: str, exec_dir: str):
        # Configuration scripts should save the project.
        configure_status = subprocess.run([sys.executable, self.build_script_path], capture_output=True, cwd=source_dir)
        if configure_status.returncode:
            G_LOGGER.critical(f"Failed to run build configuration script: {self.build_script_path} in {source_dir} with:\n{utils.subprocess_output(configure_status)}")

        saved_project = os.path.join(source_dir, self.project_save_path)
        if not os.path.exists(saved_project):
            G_LOGGER.critical(f"Project was not saved to: {saved_project}. Please ensure this path is correct, and that the build configuration script in {self.build_script_path} is saving the project")

        proj = Project.load(saved_project)
        proj.install(header_install_path=header_dir, library_install_path=lib_dir, executable_install_path=exec_dir, dry_run=False)
