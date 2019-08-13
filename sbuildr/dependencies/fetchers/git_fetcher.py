from sbuildr.dependencies.fetcher import DependencyFetcher
from sbuildr.misc import utils
import subprocess
import sys
import os

# TODO: Support local repos (they should be copied to the destination instead of downloaded)
class GitFetcher(DependencyFetcher):
    def __init__(self, url):
        """
        A dependency fetcher that fetches git repositories.

        :param url: The URL at which the repository is located. It will be cloned from this location.
        """
        self.url = url
        super().__init__(os.path.splitext(os.path.basename(self.url))[0])

    def fetch(self, dest_dir: str, version: str):
        """
        If no version is provided, uses the tip of the main branch.
        """
        clone_status = subprocess.run(["git", "clone", self.url, dest_dir], capture_output=True)
        # TODO: Error checking here? Pull may fail if this is a local repo.
        pull_status = subprocess.run(["git", "pull"], capture_output=True, cwd=dest_dir)

        tag = f"v{version}"
        checkout_status = subprocess.run(["git", "checkout", tag], capture_output=True, cwd=dest_dir)
        if checkout_status.returncode:
            G_LOGGER.critical(f"Failed to checkout {tag} with:\n{utils.subprocess_output(checkout_status)}")
