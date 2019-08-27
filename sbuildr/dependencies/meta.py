from sbuildr.graph.node import Library
from typing import Dict, List, Union

import pickle
import os

class LibraryMetadata(object):
    def __init__(self, path: str, libs: List[str], lib_dirs: List[str]):
        self.path = path
        self.libs = libs
        self.lib_dirs = lib_dirs

class DependencyMetadata(object):
    def __init__(self, libraries: Dict[str, LibraryMetadata], include_dirs: List[str]):
        """
        Contains metadata about a dependency.

        :param libraries: Maps library names to libs/lib_dirs.
        :param include_dirs: Any include directories required by this dependency.
        """
        self.libraries: Dict[str, LibraryMetadata] = libraries
        self.include_dirs = include_dirs
        self.META_API_VERSION = 1.1 # Must be tied to the instance due to how pickling works.

    # Returns None if the loaded Metadata is incompatible, or does not exist.
    @staticmethod
    def load(path: str) -> Union[None, "DependencyMetadata"]:
        if not os.path.exists(path):
            return None

        with open(path, "rb") as f:
            meta = pickle.load(f)
        if meta.API_VERSION != DependencyMetadata.API_VERSION:
            return None
        return meta

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)
