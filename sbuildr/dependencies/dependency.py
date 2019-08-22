from sbuildr.dependencies.builder import DependencyBuilder
from sbuildr.dependencies.fetcher import DependencyFetcher
from sbuildr.dependencies.meta import DependencyMetadata, LibraryMetadata
from sbuildr.graph.node import Library
from sbuildr.logger import G_LOGGER
from sbuildr.misc import paths

from typing import List
import os

# TODO: This does not support executables
class Dependency(object):
    CACHE_SOURCES_SUBDIR = "sources"
    CACHE_PACKAGES_SUBDIR = "packages"

    PACKAGE_HEADER_SUBDIR = "include"
    PACKAGE_LIBRARY_SUBDIR = "lib"
    PACKAGE_EXECUTABLE_SUBDIR = "bin"
    METADATA_FILENAME = "meta.pkl"

    # TODO: Make cache_root propagate to nested dependencies.
    def __init__(self, fetcher: DependencyFetcher, builder: DependencyBuilder, version: str, cache_root: str=paths.dependency_cache_root()):
        """
        Manages a fetcher-builder pair for a single dependency.

        :param fetcher: The fetcher to use to retrieve the source code for this dependency.
        :param builder: The builder to use to generate build artifacts for this dependency.
        :param version: The version number of the dependency to fetch.
        :param cache_root: The root directory to use for caching dependencies.
        """
        self.fetcher = fetcher
        self.builder = builder
        self.name = self.fetcher.dependency_name
        self.version = version
        self.cache_root = cache_root
        self.package_root = os.path.join(self.cache_root, Dependency.CACHE_PACKAGES_SUBDIR, f"{self.name}-{self.version}")
        self.header_dir = os.path.join(self.package_root, Dependency.PACKAGE_HEADER_SUBDIR)
        self.lib_dir = os.path.join(self.package_root, Dependency.PACKAGE_LIBRARY_SUBDIR)
        self.exec_dir = os.path.join(self.package_root, Dependency.PACKAGE_EXECUTABLE_SUBDIR)
        self.libraries: Dict[str, Library] = {}


    # TODO: Need a switch to force the fetch.
    # TODO: Need to test both code paths - with and without metadata saved.
    def setup(self) -> DependencyMetadata:
        """
        Fetch, build, and install the dependency if the dependency does not exist in the cache. After setting up the dependency, all references to libraries in the dependency are updated according to the metadata reported by the builder. If the dependency is found in the cache, loads the metadata from the cache instead.

        :returns: A list of include directories from this dependency.
        """
        metadata_path = os.path.join(self.package_root, Dependency.METADATA_FILENAME)
        meta = DependencyMetadata.load(metadata_path)
        if not meta:
            G_LOGGER.info(f"{self.package_root} does not contain package metadata. Fetching dependency.")
            # Fetch
            dep_dir = os.path.join(self.cache_root, Dependency.CACHE_SOURCES_SUBDIR, self.name)
            self.fetcher.fetch(dep_dir, self.version)
            # Install
            meta = self.builder.install(dep_dir, header_dir=self.header_dir, lib_dir=self.lib_dir, exec_dir=self.exec_dir)
            meta.save(metadata_path)

        # Next, update all libraries that have been requested from this dependency.
        for name, lib in self.libraries.items():
            if name not in meta.libraries:
                G_LOGGER.critical(f"Requested library: {name} is not present in dependency: {self.name}")
            metalib = meta.libraries[name]
            lib.libs.extend(metalib.libs)
            lib.lib_dirs.extend(metalib.lib_dirs)
            G_LOGGER.verbose(f"Correcting library: {name} to {lib}")

        return meta


    def library(self, name: str) -> "DependencyLibrary":
        # The library's lib_dirs and libs will be updated during setup in project's configure_graph.
        self.libraries[name] = Library(path=os.path.join(self.lib_dir, paths.name_to_libname(name)))
        return DependencyLibrary(self, self.libraries[name])

    def __str__(self) -> str:
        return f"{self.name}: Version {self.version} in {self.package_root}"

    def __repr__(self) -> str:
        return self.__str__()

# Tracks a library and the dependency from which it originates.
class DependencyLibrary(object):
    def __init__(self, dependency: Dependency, library: Library):
        """
        Represents a library that comes from a dependency. It is important that instances of this class not be cloned, as they will be updated in-place.
        """
        self.dependency = dependency
        self.library = library

# TODO: Add DependencyHeader that tracks a dependency and Header node
class DependencyHeader(object):
    pass
