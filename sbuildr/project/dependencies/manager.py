from typing import List, Tuple
from sbuildr.project.dependencies.builders.builder import DependencyBuilder
from sbuildr.project.dependencies.fetchers.fetcher import DependencyFetcher

# TODO: This class should track a single dependency, and should be provided on a per target basis.
# TODO: Should have a library(), and executable() to specify what exactly we need from the dependency
# TODO: SBuildr will need a way to only install headers.
# TODO: Configure needs to take targets as an option, so only non-test targets can be configured. 
class DependencyManager(object):
    def __init__(self, dependencies: List[Tuple[DependencyFetcher, DependencyBuilder]]):
        """
        Manages a group of pairs of fetchers and builders.
        """
        self.dependencies = dependencies
