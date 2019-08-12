from sbuildr.graph.node import Library
from typing import Dict, List

class DependencyMetadata(object):
    def __init__(self, libraries: Dict[str, Library], include_dirs: List[str]):
        self.libraries: Dict[str, Library] = libraries
        self.include_dirs = include_dirs

    @staticmethod
    def load(path: str):
        with open(path, "rb") as f:
            return pickle.load(f)

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)
