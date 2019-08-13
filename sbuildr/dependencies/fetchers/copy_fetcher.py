from sbuildr.dependencies.fetcher import DependencyFetcher
from sbuildr.logger import G_LOGGER

import filecmp
import shutil
import os

class CopyFetcher(DependencyFetcher):
    def __init__(self, path: str):
        """
        A dependency fetcher that copies source code from the specified path.

        :param path: A path to the source code to copy. This fetcher will only copy if the path is newer than the cached source from any previous copies.
        """
        self.path = path
        super().__init__(os.path.basename(self.path))

    def fetch(self, dest_dir: str, version: str=None) -> str:
        if version is not None:
            G_LOGGER.warning(f"The copy fetcher ignores version numbers. Please ensure that {self.path} contains version {version} of the project.")
        # Only copy if dest_dir is out of date.
        should_copy = not os.path.exists(dest_dir) or filecmp.dircmp(self.path, dest_dir).left_only or os.path.getmtime(self.path) > os.path.getmtime(dest_dir)
        if should_copy:
            shutil.rmtree(dest_dir, ignore_errors=True)
            shutil.copytree(self.path, dest_dir)
        # Use the timestamp of the source, as dest_dir timestamp will change every time the source is copied.
        return str(os.path.getmtime(self.path))
