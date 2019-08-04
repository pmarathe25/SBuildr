from typing import List

class DepInfo(object):
    def __init__(self, name: str, path: str, version_tags: List[str]=[]):
        """
        Keeps track of information about a fetched dependency.

        :param name: The name of the dependency. This should generally match the name of the library/project being fetched.
        :param path: The path where the dependency was fetched.
        :param version_tags: A list of version tags identifying the fetched version of the dependency. These may be commit hashes, version numbers, or git tags. These will be used by the dependency manager for caching dependencies. More than one version tag may be specified, in which case, any matching tag will be treated as a match for caching purposes.
        """
        self.name = name
        self.path = path
        self.version_tags = version_tags

class DependencyFetcher(object):
    def __init__(self):
        """
        A fetcher that retrieves a dependency for use with a DependencyBuilder.
        """
        pass

    def fetch(self, dir: str) -> DepInfo:
        """
        Fetches the dependency into the specified location.

        :param dir: An absolute path to a directory to which to write the fetched dependency. The fetcher may overwrite any existing files in this location.

        :returns: Information about the retrieved dependency.
        """
        raise NotImplementedError()
