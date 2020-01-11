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
    def __init__(self, fetcher: DependencyFetcher, builder: DependencyBuilder, cache_root: str=paths.dependency_cache_root()):
        """
        Manages a fetcher-builder pair for a single dependency.

        :param fetcher: The fetcher to use to retrieve the source code for this dependency.
        :param builder: The builder to use to generate build artifacts for this dependency.
        :param version: The version number of the dependency to fetch.
        :param cache_root: The root directory to use for caching dependencies.
        """
        self.cache_root = cache_root
        self.fetcher = fetcher
        self.fetcher.set_dest_dir(os.path.join(self.cache_root, Dependency.CACHE_SOURCES_SUBDIR, self.fetcher.dependency_name))
        self.builder = builder
        self.libraries: Dict[str, Library] = {}

        self.package_root = None
        self.version = None


    def library(self, name: str) -> "DependencyLibrary":
        # The library's lib_dirs and libs will be updated during setup in project's configure().
        if name not in self.libraries:
            self.libraries[name] = Library(name=name)
        return DependencyLibrary(self, self.libraries[name])


    def include_dir(self) -> str:
        """
        Return the directory containing the headers required for this dependency. Must be called after setup().
        """
        if not self.package_root:
            G_LOGGER.critical(f"include_dir() must not be called before setup()")
        return os.path.join(self.package_root, Dependency.PACKAGE_HEADER_SUBDIR)


    # TODO: Need to test both code paths - with and without metadata saved.
    def setup(self, force=False) -> DependencyMetadata:
        """
        Fetch, build, and install the dependency if the dependency does not exist in the cache. After setting up the dependency, all references to libraries in the dependency are updated according to the metadata reported by the builder. If the dependency is found in the cache, loads the metadata from the cache instead.

        :param force: Force the dependency to be fetched, built and installed, even if it already exists in the cache.

        :returns: A list of include directories from this dependency.
        """
        # Create the destination directory for the fetcher
        os.makedirs(self.fetcher.dest_dir, exist_ok=True)

        def update_package_root():
            name = self.fetcher.dependency_name
            self.version = self.fetcher.version()
            dir = f"{name}-{self.version}" if self.version else name
            self.package_root = os.path.join(self.cache_root, Dependency.CACHE_PACKAGES_SUBDIR, dir)

        update_package_root()
        metadata_path = os.path.join(self.package_root, Dependency.METADATA_FILENAME)
        meta = None
        if os.path.exists(metadata_path):
            meta = DependencyMetadata.load(metadata_path)

        if force or meta is None or meta.META_API_VERSION != DependencyMetadata.META_API_VERSION:
            G_LOGGER.info(f"{self.package_root} does not contain package metadata. Fetching dependency.")
            self.fetcher.fetch()
            # Install
            lib_dir = os.path.join(self.package_root, Dependency.PACKAGE_LIBRARY_SUBDIR)
            exec_dir = os.path.join(self.package_root, Dependency.PACKAGE_EXECUTABLE_SUBDIR)
            meta = self.builder.install(self.fetcher.dest_dir, header_dir=self.include_dir(), lib_dir=lib_dir, exec_dir=exec_dir)
            meta.save(metadata_path)

        # TODO: FIXME: Make this more resilient to copies by moving this logic to Project. FileManager already tracks all dependency libraries as Library nodes.
        # Next, update all libraries that have been requested from this dependency.
        for name, lib in self.libraries.items():
            if name not in meta.libraries:
                G_LOGGER.critical(f"Requested library: {name} is not present in dependency: {self.name}")
            metalib = meta.libraries[name]
            lib.path = metalib.path
            lib.libs.extend(metalib.libs)
            lib.lib_dirs.extend(metalib.lib_dirs)
            G_LOGGER.verbose(f"Correcting library: {name} to {lib}")
        return meta


    def __str__(self) -> str:
        return f"{self.fetcher.dependency_name}"


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
