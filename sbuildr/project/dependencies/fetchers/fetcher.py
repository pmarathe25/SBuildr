from typing import List

class DependencyInfo(object):
    def __init__(self, version_tags: List[str]=[]):
        """
        Keeps track of information about a fetched dependency.

        :param version_tags: A list of version tags identifying the fetched version of the dependency. These may be commit hashes, version numbers, or git tags. These will be used by the dependency manager for caching dependencies. More than one version tag may be specified, in which case, any matching tag will be treated as a match for caching purposes.
        """
        self.version_tags = version_tags

class DependencyFetcher(object):
    def __init__(self, name):
        """
        A fetcher that retrieves a dependency for use with a DependencyBuilder.

        :param name: The name of the dependency. This should generally match the name of the library/project being fetched.
        """
        self.dependency_name = name

    def fetch(self, dest_dir: str) -> DependencyInfo:
        """
        Fetches the dependency into the specified location.

        :param dest_dir: An absolute path to the directory in which to write the fetched dependency. If the original source has the structure ``source_dir/<files>``, then the fetched structure should be ``dest_dir/<files>``. That is, the fetcher must not introduce any additional intermediate directories.

        :returns: Information about the retrieved dependency.
        """
        raise NotImplementedError()
