from sbuildr.logger import G_LOGGER

from typing import List

class DependencyFetcher(object):
    def __init__(self, name):
        self.dependency_name = name
        self.dest_dir = None


    def set_dest_dir(self, dest_dir: str):
        """
        Set the path to the directory that will be used for fetching source code.

        :param dest_dir: An absolute path to the directory in which to write the fetched dependency.
        """
        self.dest_dir = dest_dir


    def fetch(self) -> str:
        """
        Fetches the dependency into the specified location.

        :returns: The directory into which the dependency was fetched.
        """
        if not self.dest_dir:
            G_LOGGER.critical(f"Cannot fetch before setting destination directory.")


    def version(self) -> str:
        """
        Specifies the version of the dependency to be fetched. This is used for caching purposes.

        :returns: A string representing the version - for example, a commit hash or a version number.
        """
        if not self.dest_dir:
            G_LOGGER.critical(f"Cannot get version before setting destination directory.")
