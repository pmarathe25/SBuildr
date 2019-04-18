from srbuild.graph.graph import Graph
from srbuild.graph.node import Node
from srbuild.logger import G_LOGGER
from typing import Set, Dict, Tuple
import glob
import os
import re

# Match includes of the form #include <.*> and #include ".*" excluding commented out lines.
INCLUDE_REGEX = re.compile(r'(?:(?<!\/\/\s))#include [<"]([^>"]*)[>"]')
# Finds all tokens #include'd by a file.
# These are not necessarily full paths.
def _find_included(filename: str) -> Set[str]:
    with open(filename, 'r') as file:
        return set(INCLUDE_REGEX.findall(file.read()))

# TODO: Docstrings
class FileManager(object):
    def __init__(self, dirs: Set[str]=set()):
        self.files = []
        for dir in dirs:
            for path in glob.iglob(os.path.join(dir, "**"), recursive=True):
                if os.path.isfile(path):
                    self.files.append(os.path.abspath(path))
        # self.files = list(map(os.path.abspath, self.files))
        G_LOGGER.debug(f"Found {len(self.files)} files")
        G_LOGGER.verbose(f"{self.files}")
        self.include_cache: Dict[str, Set[str]] = {}
        # Keep track of all source files.
        self.source_graph = Graph()

    # TODO: Docstrings
    # Finds filename in self.files. Always returns an absolute path.
    def find(self, filename: str):
        return [path for path in self.files if path.endswith(filename)]

    # Finds all required include directories for any given file.
    def source_info(self, filename: str) -> Tuple[Node, Set[str]]:
        if filename in self.include_cache:
            include_dirs = self.include_cache[filename]
            node = self.source_graph[filename]
            G_LOGGER.verbose(f"Found {filename} in include cache with include dirs: {include_dirs}, node: {node}")
            return node, include_dirs

        G_LOGGER.verbose(f"Could not find {filename} in include cache")

        # TODO: Handle paths that start with relative paths i.e. ../ or ./
        # Such paths should always be relative to the file itself, otherwise it's an error.
        # This always returns an absolute path, since self.find always returns absolute paths.
        def _disambiguate_included_file(included: str, filename: str) -> str:
            candidates = self.find(included)
            if len(candidates) == 0:
                return None

            # Determines how "close together" files are. Smaller numbers mean they are further apart in the tree.
            def _file_proximity(path_a: str, path_b: str) -> int:
                return len(os.path.split(os.path.commonpath([path_a, path_b])))

            # Return the path that is closest to the file
            closest_path = max(candidates, key=lambda candidate: _file_proximity(candidate, filename))
            G_LOGGER.debug(f"For {filename}, determined that {closest_path} best matches include for {included}. If this is not the case, please provide a longer path in the include to disambiguate, or manually provide the correct include directories. Note, candidates were: {candidates}")
            return closest_path

        # TODO: Handle relative paths in included here.
        # TODO: FIXME: This will not work if the include has escaped characters in it.
        def _get_path_include_dir(path: str, included: str) -> str:
            # path is the full path of the included file.
            # included is the token used to include the file.
            include_dir = path[:-len(included)]
            if not os.path.isdir(include_dir):
                # It would be completely ridiculous if this actually displays ever.
                G_LOGGER.critical(f"While attempting to find include dir to use for {path} (Note: included in {filename}), found that {include_dir} does not exist!")
            return os.path.abspath(include_dir)

        # Find all included files in this file. If they are in the project, recurse over them.
        # Otherwise, assume they are external headers.
        node = self.source_graph.add(Node(filename))
        include_dirs = set()
        external_includes = set()
        included_files = _find_included(filename)
        for included in included_files:
            # Determines the most likely file path based on an include.
            path = _disambiguate_included_file(included, filename)
            if path:
                G_LOGGER.verbose(f"For included token {included}, found path: {path}")
                # The include dir for a path for filename depends on how exactly the path was included in filename.
                include_dir = _get_path_include_dir(path, included)
                G_LOGGER.verbose(f"For path {path}, using include dir: {include_dir}")
                include_dirs.add(include_dir)
                # Also recurse over any include directories needed for the path itself
                path_node, path_include_dirs = self.source_info(path)
                node.add_input(path_node)
                include_dirs.update(path_include_dirs)
            else:
                external_includes.add(included)
        if external_includes:
            G_LOGGER.info(f"For {filename}, could not find headers: {external_includes}. Assuming they are external. If this is not the case, please add the appropriate directories to the project definition.")
        G_LOGGER.debug(f"For {filename}, found include dirs: {include_dirs}")
        self.include_cache[filename] = include_dirs
        G_LOGGER.verbose(f"Updated include cache to: {self.include_cache}")
        G_LOGGER.verbose(f"Updated source graph to: {self.source_graph}")
        return node, include_dirs
