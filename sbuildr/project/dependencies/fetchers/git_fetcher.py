from sbuildr.project.dependencies.fetchers.fetcher import DependencyFetcher
from sbuildr.misc import utils
import subprocess
import sys
import os

# TODO: Support local repos (they should be copied to the destination instead of downloaded)
class GitFetcher(DependencyFetcher):
    # TODO: Support version numbers
    def __init__(self, url, commit: str=None, tag: str=None, branch: str="master"):
        """
        A dependency fetcher that fetches git repositories. It is also possible to specify a commit, tag, or branch to checkout. If more than one of these is specified, ``commit`` takes precedence over ``tag``, which takes precedence over ``branch``

        :param url: The URL at which the repository is located. It will be cloned from this location.
        :param commit: The commit hash to checkout.
        :param tag: The tag to checkout.
        :param branch: The branch to checkout. Defaults to "master".
        """
        self.url = url
        self.commit = commit
        self.tag = tag
        self.branch = branch
        super().__init__(os.path.splitext(os.path.basename(self.url))[0])

    def fetch(self, dest_dir: str) -> str:
        clone_status = subprocess.run(["git", "clone", self.url, dest_dir], capture_output=True)

        # TODO: Error checking here? Pull may fail if this is a local repo.
        checkout = self.commit or self.tag or self.branch
        pull_status = subprocess.run(["git", "pull"], capture_output=True, cwd=dest_dir)
        checkout_status = subprocess.run(["git", "checkout", checkout], capture_output=True, cwd=dest_dir)
        if checkout_status.returncode:
            G_LOGGER.critical(f"Failed to checkout {checkout} with:\n{utils.subprocess_output(checkout_status)}")

        # TODO: Error checking here?
        head_status = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, cwd=dest_dir)
        commit_hash = head_status.stdout.strip().decode(sys.stdout.encoding)
        return commit_hash