from typing import Dict, List

import pickle

class DependencyMetadata(object):
    def __init__(self, lib_dirs: Dict[str, List[str]], include_dirs: List[str]):
        """
        Contains metadata about a dependency.

        :param lib_dirs: Maps library names to the directories required to load them.
        :param include_dirs: Any include directories required by this dependency. 
        """
        self.lib_dirs: Dict[str, Library] = lib_dirs
        self.include_dirs = include_dirs

    @staticmethod
    def load(path: str) -> "DependencyMetadata":
        with open(path, "rb") as f:
            return pickle.load(f)

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)
