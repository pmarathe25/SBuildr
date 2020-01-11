from sbuildr.graph.node import Node, SourceNode
from sbuildr.graph.graph import Graph
from sbuildr.logger import G_LOGGER

from typing import Set, Dict, Tuple, List
import shutil
import glob
import os
import re

# Match includes of the form #include <.*> and #include ".*" excluding commented out lines.
# TODO: FIXME: This is not smart enough to understand preprocessor conditional blocks
INCLUDE_REGEX = re.compile(r'(?:(?<!\/\/\s))#include [<"]([^>"]*)[>"]')
# Finds all tokens #include'd by a file.
# These are not necessarily full paths.
def _find_included(filename: str) -> Set[str]:
    with open(filename, 'r') as file:
        return set(INCLUDE_REGEX.findall(file.read()))

def _is_in_directory(path: str, dir: str):
    # e.g. for _is_in_directory(/my/dir/my/path, /my/dir/), commonpath == dir.
    # This is always the case if path is in dir.
    return os.path.commonpath([path, dir]) == dir

# Checks if path is in any of the specified dirs.
def _is_in_directories(path: str, dirs: Set[str]):
    return any([_is_in_directory(path, dir) for dir in dirs])

class FileManager(object):
    # The root directory is used for converting relative paths to absolute paths.
    def __init__(self, root_dir: str, dirs: Set[str]=set(), exclude_dirs: Set[str]=set(), writable_dirs: Set[str]=set()):
        self.exclude_dirs: Set[str] = exclude_dirs
        # writable_dirs are the only locations to which FileManager is allowed to write.
        self.writable_dirs: Set[str] = writable_dirs
        G_LOGGER.verbose(f"Excluded directories: {exclude_dirs}. Writable directories: {writable_dirs}")

        # Include dirs/"header" files are only considered when searching for includes.
        self.include_dirs: List[str] = []
        self.header_files: List[str] = [] # List to enable header priority

        self.files: Set[str] = set()

        self.root_dir = os.path.abspath(root_dir)
        if not os.path.isdir(self.root_dir):
            G_LOGGER.critical(f"Root Directory: {self.root_dir} does not exist, or is not a directory.")
        self.add_dir(self.root_dir)

        # Remove directories that are within exclude_dirs after converting all directories to abspaths.
        for dir in dirs:
            self.add_dir(dir)
        G_LOGGER.debug(f"Found {len(self.files)} files")
        G_LOGGER.verbose(f"{self.files}")
        # Keep track of all files relevant to building the project.
        self.graph = Graph()


    # Finds all files recursively in the specified directory.
    def _files_in_dir(self, dir: str):
        dir = self.abspath(dir)
        G_LOGGER.verbose(f"Searching for files in: {dir}")
        files = []
        for path in glob.iglob(os.path.join(dir, "**"), recursive=True):
            if os.path.isfile(path) and not _is_in_directories(path, self.exclude_dirs):
                files.append(os.path.abspath(path))
            else:
                G_LOGGER.verbose(f"Rejecting path: {path}, because it is either not a file, or falls in one of the excluded directories.")
        return files

    # TODO: FIXME: This does not handle directories inside exclude directories correctly.
    def add_dir(self, dir: str):
        self.files.update(self._files_in_dir(dir))

    def add_include_dir(self, dir: str):
        if dir not in self.include_dirs:
            self.include_dirs.append(dir)
            self.header_files.extend(self._files_in_dir(dir))

    # Adds the specified directory to exclude_dirs, then returns the absolute path to the added directory.
    def add_exclude_dir(self, dir: str) -> str:
        absdir = self.abspath(dir)
        self.exclude_dirs.add(absdir)
        # Remove any files that are in the new exclude directory.
        self.files = set([file for file in self.files if not _is_in_directory(file, absdir)])
        G_LOGGER.verbose(f"Updated files to: {self.files}")
        return absdir

    # Adds the specified directory to writable_dirs, then returns the absolute path to the added directory.
    def add_writable_dir(self, dir: str) -> str:
        absdir = self.abspath(dir)
        self.writable_dirs.add(absdir)
        return absdir

    # Recursively creates all parent directories required to create dir_path.
    # Returns whether the directory was created inside the exclude directory.
    # If it is not a subdirectory of the exclude directory, returns False.
    def mkdir(self, dir_path: str) -> bool:
        if _is_in_directories(dir_path, self.writable_dirs):
            os.makedirs(dir_path, exist_ok=True)
            return True
        return False

    # Remove files and directories, but only if they are within the exclude directories.
    # Returns whether the path was located in the build directory..
    def rm(self, path: str) -> bool:
        if _is_in_directories(path, self.writable_dirs):
            shutil.rmtree(path, ignore_errors=True)
            G_LOGGER.info(f"Removed: {path}")
            return True
        return False

    # Converts path to an absolute path. First checks if it exists relative to the root directory,
    # otherwise falls back to cwd.
    def abspath(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        # Prefer a path relative to the root unless the absolute path relative to cwd exists.
        in_root_path = os.path.abspath(os.path.join(self.root_dir, path))
        abspath = os.path.abspath(path)
        if not os.path.exists(abspath):
            return in_root_path
        return abspath

    # Finds filename in self.files. Always returns absolute paths.
    # If the file exists but is not in this FileManager's tracked directories, returns an empty list.
    # The returned list is in order of proximity to the root. The first element is closest to the root.
    # If search_include_dirs is True, then also looks for files in include_dirs
    def find(self, path: str, search_include_dirs=False) -> List[str]:
        all_files = list(self.files) + self.header_files if search_include_dirs else self.files
        # TODO: endswith is not a good way to do this. Need a path-separator-aware endswith.
        candidates = set([fpath for fpath in all_files if fpath.endswith(path)])
        # Prefer shorter paths, i.e. closer to the root.
        candidates = list(sorted(candidates, key=lambda elem: len(elem)))
        # Also check if this exists when converted to an absolute path.
        # This should be the highest priority.
        path = self.abspath(path)
        if os.path.exists(path) and path not in candidates:
            candidates.insert(0, path)
        return candidates

    # Adds an external path to the source graph.
    def external(self, path: str) -> Node:
        return self.graph.add(Node(path))

    # Finds the given path in self.files and returns the SourceNode for it.
    # The SourceNode is added to the graph if it does not already exist.
    def source(self, path: str) -> SourceNode:
        candidates = self.find(path)
        if len(candidates) > 1:
            G_LOGGER.warning(f"For {path}, found multiple candidates: {candidates}. Using {candidates[0]}. If this is incorrect, please disambiguate by providing either an absolute path, or a longer relative path.")
        elif len(candidates) == 0:
            G_LOGGER.critical(f"Could not find {path}. Does it exist?")
        path = candidates[0]
        node = self.graph.find_node_with_path(path)
        if not node:
            return self.graph.add(SourceNode(candidates[0]))
        return node

    def scan_all(self) -> None:
        # scan() will modify the graph, so cannot iterate over values() directly
        source_nodes = [node for node in self.graph if isinstance(node, SourceNode)]
        G_LOGGER.verbose(f"Scanning source nodes: {source_nodes}")
        [self.scan(node) for node in source_nodes]

    # Finds all required include directories for a given managed file. Adds nodes to the graph if missing.
    def scan(self, node: str) -> None:
        G_LOGGER.debug(f"Scanning {node.path}")

        # Finds the file path for the file included in `include_path` by the `included_token` token.
        # This always returns an absolute path, since self.find always returns absolute paths.
        def disambiguate_included_file(included_token: str, include_path: str) -> str:
            # TODO: Handle paths that start with ../
            # Such paths should always be relative to the file itself, otherwise it's an error.
            if include_path.startswith(os.path.pardir):
                raise NotImplementedError(f"FileManager does not currently support includes containing {os.path.pardir}")

            candidates = self.find(included_token, search_include_dirs=True)
            if len(candidates) == 0:
                return None

            # TODO: Move this into misc.paths, add test case.
            # Determines how "close together" files are. Smaller numbers mean they are further apart in the tree.
            def file_proximity(path_a: str, path_b: str) -> int:
                return len(os.path.commonpath([path_a, path_b]).split(os.path.sep))

            # Return the path that is closest to the including file
            closest_path = max(candidates, key=lambda candidate: file_proximity(candidate, include_path))

            if len(candidates) > 1:
                G_LOGGER.warning(f"For {include_path}, found multiple possible headers, but determined that {closest_path} best matches include for {included_token}. If this is not the case, please provide a longer path in the include to disambiguate, or manually provide the correct include directories. Note, candidates were: {candidates}")
            return closest_path

        # TODO: Handle relative paths in included here.
        # TODO: FIXME: This will not work if the include has escaped characters in it.
        def get_path_include_dir(included_path: str, included_token: str) -> str:
            # included_path is the full path of the included file.
            # included_token is the token used to include the file.
            # Absolute paths do not require include directories.
            if os.path.isabs(included_token):
                return None
            include_dir = included_path[:-len(included_token)]
            if not os.path.isdir(include_dir):
                # It would be completely ridiculous if this actually displays ever.
                G_LOGGER.critical(f"While attempting to find include dir to use for {included_path} (Note: included in {path}), found that {include_dir} does not exist!")
            return os.path.abspath(include_dir)

        # Find all included files in this file. If they are in the project, recurse over them.
        # Otherwise, assume they are external headers.
        include_dirs = set()
        external_includes = set()
        path = node.path
        included_files = _find_included(path)
        for included in included_files:
            # Determines the most likely file path based on an include.
            included_path = disambiguate_included_file(included, path)
            if included_path:
                G_LOGGER.verbose(f"For included token {included}, found path: {included_path}")
                # The include dir for a path for path depends on how exactly the path was included in path.
                include_dir = get_path_include_dir(included_path, included)
                if include_dir:
                    G_LOGGER.verbose(f"For path {included_path}, using include dir: {include_dir}")
                    include_dirs.add(include_dir)
                # Also recurse over any include directories needed for the path itself
                included_path_node = self.source(included_path)
                if included_path_node.include_dirs is None:
                    G_LOGGER.verbose(f"{included_path_node} does not specify include directories. Scanning file.")
                    self.scan(included_path_node)
                include_dirs.update(included_path_node.include_dirs)
                node.add_input(included_path_node)
            else:
                external_includes.add(included)
        if external_includes:
            G_LOGGER.debug(f"For {path}, could not find headers: {external_includes}. Assuming they are external. If this is not the case, please add the appropriate directories to the project definition.")

        include_dirs = sorted(include_dirs)
        node.include_dirs = include_dirs
        G_LOGGER.debug(f"For {path}, found include dirs: {include_dirs}")
        G_LOGGER.verbose(f"Updated source graph to: {self.graph}")
