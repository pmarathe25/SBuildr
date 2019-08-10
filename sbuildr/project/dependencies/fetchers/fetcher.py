from typing import List

class DependencyFetcher(object):
    def __init__(self, name):
        self.dependency_name = name

    # TODO: Support better options for version, like >, <, == etc.
    def fetch(self, dest_dir: str, version: str):
        """
        Fetches the dependency into the specified location.

        :param dest_dir: An absolute path to the directory in which to write the fetched dependency. If the original source has the structure ``source_dir/<files>``, then the fetched structure should be ``dest_dir/<files>``. That is, the fetcher must not introduce any additional intermediate directories.
        :param version: The version number of the dependency to fetch.
        """
        raise NotImplementedError()
