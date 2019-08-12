from sbuildr.project.dependencies.builders.builder import DependencyBuilder
from sbuildr.project.dependencies.fetchers.fetcher import DependencyFetcher
from sbuildr.misc import paths

import os

CACHE_SOURCES_SUBDIR = "sources"
CACHE_PACKAGES_SUBDIR = "packages"

PACKAGE_HEADER_SUBDIR = "include"
PACKAGE_LIBRARY_SUBDIR = "lib"
PACKAGE_EXECUTABLE_SUBDIR = "bin"

# TODO: Should have a library(), and executable() to specify what exactly we need from the dependency
# TODO: Dependency fetching should happen in configure, with a targets parameter. This way you can fetch only for those targets you need to install.
# TODO: FileManager needs add_include_dir so that include dirs from dependencies can be propagated.
# TODO: Header scanning will need to be deferred once again until configure_backend
class Dependency(object):
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

    def setup(self) -> str:
        """
        Fetch, build, and install the dependency if the dependency does not exist in the cache. If the dependency is found in the cache, does nothing.

        :returns: An absolute path to the root of the package.
        """
        package_root = os.path.join(self.cache_root, CACHE_PACKAGES_SUBDIR, f"{self.name}-{self.version}")

        if not os.path.exists(package_root):
            # Fetch
            dep_dir = os.path.join(self.cache_root, CACHE_SOURCES_SUBDIR, self.name)
            self.fetcher.fetch(dep_dir, self.version)
            # Install
            header_dir = os.path.join(package_root, PACKAGE_HEADER_SUBDIR)
            lib_dir = os.path.join(package_root, PACKAGE_LIBRARY_SUBDIR)
            exec_dir = os.path.join(package_root, PACKAGE_EXECUTABLE_SUBDIR)
            self.builder.install(dep_dir, header_dir=header_dir, lib_dir=lib_dir, exec_dir=exec_dir)

        # TODO(0): If the package_root exists, need some way to get information about libs/execs from it.
        # Need at least path and ld_dirs. Builder will need to return this when installing above.
        # Need something similar for include dirs as well
        return package_root
