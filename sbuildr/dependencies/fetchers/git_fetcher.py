from sbuildr.dependencies.fetcher import DependencyFetcher
from sbuildr.logger import G_LOGGER
from sbuildr.misc import utils
import subprocess
import sys
import os

# TODO: Support local repos (they should be copied to the destination instead of downloaded)
# TODO: Support better options for version, like >, <, == etc.
class GitFetcher(DependencyFetcher):
    def __init__(self, url, commit: str = None, tag: str = None, branch: str = "master"):
        """
        A dependency fetcher that fetches git repositories.

        :param url: The URL at which the repository is located. It will be cloned from this location.
        """
        self.url = url
        self.commit = commit
        self.tag = tag
        self.branch = branch
        super().__init__(os.path.splitext(os.path.basename(self.url))[0])

    def fetch(self) -> str:
        super().fetch()
        subprocess.run(["git", "init"], cwd=self.dest_dir, capture_output=True)

        # Stash any local changes made by external sources
        G_LOGGER.info(f"Stashing changes in {self.dest_dir}")
        subprocess.run(["git", "stash"], capture_output=False, cwd=self.dest_dir)

        checkout = self.commit or self.tag or self.branch
        G_LOGGER.info(f"Pulling: {self.url} at {checkout} into {self.dest_dir}")
        # # TODO: Error checking here? Pull may fail if this is a local repo.
        subprocess.run(
            ["git", "pull", "--force", "--recurse-submodules", "--tags", self.url, checkout],
            capture_output=False,
            cwd=self.dest_dir,
        )

        G_LOGGER.info(f"Checking out: {checkout}")
        checkout_status = subprocess.run(["git", "checkout", checkout], capture_output=True, cwd=self.dest_dir)
        if checkout_status.returncode:
            G_LOGGER.critical(f"Failed to checkout {checkout} with:\n{utils.subprocess_output(checkout_status)}")
        return self.dest_dir

    def version(self) -> str:
        super().version()
        if self.commit:
            return self.commit
        self.fetch()
        head_status = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, cwd=self.dest_dir)
        return head_status.stdout.strip().decode(sys.stdout.encoding)
