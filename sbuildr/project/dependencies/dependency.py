from sbuildr.project.dependencies.builders.builder import DependencyBuilder
from sbuildr.project.dependencies.fetchers.fetcher import DependencyFetcher
import pathlib

# TODO: Move this into project
def default_cache_root():
    return os.path.join(pathlib.Path.home(), ".sbuildr")

# TODO: This class should track a single dependency, and should be provided on a per target basis.
# TODO: Should have a library(), and executable() to specify what exactly we need from the dependency
# TODO: SBuildr will need a way to only install headers.
# TODO: Configure needs to take targets as an option, so only non-test targets can be configured.
class Dependency(object):
    def __init__(self, fetcher: DependencyFetcher, builder: DependencyBuilder):
        """
        Manages a fetcher-builder pair for a single dependency.

        :param fetcher: The fetcher to use to retrieve the source code for this dependency.
        :param builder: The builder to use to generate build artifacts for this dependency.
        """
        self.fetcher = fetcher
        self.builder = builder

    def setup(self):
        """
        Fetch, build, and install the dependency. This function will only build and install if the fetched dependency differs from the existing dependency, as per the version tag.
        """
        pass
