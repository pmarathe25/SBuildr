from sbuildr.dependencies.fetcher import DependencyFetcher

import shutil
import os


class CopyFetcher(DependencyFetcher):
    def __init__(self, path: str, version: str = ""):
        """
        A dependency fetcher that copies source code from the specified path.

        :param path: A path to the source code to copy. This fetcher will only copy if the path is newer than the cached source from any previous copies. The path should not be relative to the project, as that will break nested dependencies.
        :param version: The version of the dependency at the specified path. This is optional, and is used for caching dependency source code.
        """
        self.path = path
        self.version_tag = version
        super().__init__(os.path.basename(self.path))

    def fetch(self) -> str:
        super().fetch()
        shutil.rmtree(self.dest_dir, ignore_errors=True)
        return shutil.copytree(self.path, self.dest_dir)

    def version(self) -> str:
        super().version()
        return self.version_tag
