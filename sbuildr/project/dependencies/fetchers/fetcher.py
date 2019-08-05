from typing import List

class DependencyFetcher(object):
    def __init__(self, name):
        """
        A fetcher that retrieves a dependency for use with a DependencyBuilder.

        :param name: The name of the dependency. This should generally match the name of the library/project being fetched.
        """
        self.dependency_name = name

    def fetch(self, dest_dir: str) -> str:
        """
        Fetches the dependency into the specified location.

        :param dest_dir: An absolute path to the directory in which to write the fetched dependency. If the original source has the structure ``source_dir/<files>``, then the fetched structure should be ``dest_dir/<files>``. That is, the fetcher must not introduce any additional intermediate directories.

        :returns: A version tag identifying the fetched version of the dependency. This may be a commit hash, version number, or git tag. This will be used by the dependency manager for caching dependencies.
        """
        raise NotImplementedError()
