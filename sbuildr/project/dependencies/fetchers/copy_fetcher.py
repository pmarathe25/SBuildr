from sbuildr.project.dependencies.fetchers.fetcher import DependencyFetcher

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

    def fetch(self, dest_dir: str) -> str:
        # Only copy if dest_dir is out of date.
        should_copy = filecmp.dircmp(self.path, dest_dir).left_only or not os.path.exists(dest_dir) or os.path.getmtime(self.path) > os.path.getmtime(dest_dir)
        if should_copy:
            shutil.rmtree(dest_dir)
            shutil.copytree(self.path, dest_dir)
        return str(os.path.getmtime(dest_dir))
