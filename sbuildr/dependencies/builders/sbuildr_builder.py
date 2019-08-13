from sbuildr.dependencies.builder import DependencyBuilder
from sbuildr.dependencies.meta import DependencyMetadata
from sbuildr.project.project import Project
from sbuildr.graph.node import Library
from sbuildr.logger import G_LOGGER
from sbuildr.misc import utils
import subprocess
import sys
import os

class SBuildrBuilder(DependencyBuilder):
    def __init__(self, build_script_path: str="build.py", project_save_path: str=Project.DEFAULT_SAVED_PROJECT_NAME, install_profile=None):
        f"""
        Builds projects using the SBuildr build system.

        :param build_script_path: The path to the build script, relative to the project root. Defaults to "build.py".
        :param project_save_path: The path at which the build script saves the project. Defaults to {Project.DEFAULT_SAVED_PROJECT_NAME}
        :param install_profile: The profile to use when building targets to install. Defaults to the project's default install profile.
        """
        self.build_script_path = build_script_path
        self.project_save_path = project_save_path
        self.install_profile = install_profile

    def install(self, source_dir: str, header_dir: str, lib_dir: str, exec_dir: str) -> DependencyMetadata:
        # Configuration scripts should save the project.
        configure_status = subprocess.run([sys.executable, self.build_script_path], capture_output=True, cwd=source_dir, env={"PYTHONPATH": os.pathsep.join(sys.path)})
        if configure_status.returncode:
            G_LOGGER.critical(f"Failed to run build configuration script: {self.build_script_path} in {source_dir} with:\n{utils.subprocess_output(configure_status)}")

        saved_project = os.path.join(source_dir, self.project_save_path)
        if not os.path.exists(saved_project):
            G_LOGGER.critical(f"Project was not saved to: {saved_project}. Please ensure this path is correct, and that the build configuration script in {self.build_script_path} is saving the project")

        project = Project.load(saved_project)

        self.install_profile = self.install_profile or project.install_profile()
        project.fetch_dependencies(project.install_targets())
        project.configure_graph(project.install_targets(), [self.install_profile])
        project.configure_backend()
        project.build(project.install_targets(), [self.install_profile])

        project.install(targets=project.install_targets(), profile_names=[self.install_profile], header_install_path=header_dir, library_install_path=lib_dir, executable_install_path=exec_dir, dry_run=False)

        libraries = {}
        for name, target in project.libraries.items():
            if not target.internal:
                lib = target[self.install_profile]
                libraries[name] = Library(path=lib.path, libs=lib.libs, lib_dirs=lib.lib_dirs)
        include_dirs = project.files.include_dirs
        return DependencyMetadata(libraries, include_dirs)
