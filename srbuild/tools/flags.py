from srbuild.logger import G_LOGGER
from typing import Union
import enum

# This is required to make the build system truly platform-agnostic.
# The same high-level options should work everywhere.
class BuildFlags(object):
    def __init__(self):
        self._o: str = None
        self._std: str = None
        self._march: str = None
        self._fpic: bool = False
        # Distinguishes shared library from executable.
        self._shared: bool = False

    def O(self, level: Union[int, str]) -> 'BuildFlags':
        self._o = str(level).strip()
        return self

    def std(self, year: Union[int, str]) -> 'BuildFlags':
        self._std = str(year).strip()
        return self

    def march(self, type: str) -> 'BuildFlags':
        self._march = str(type).strip()
        return self

    def fpic(self) -> 'BuildFlags':
        self._fpic = True
        return self

    def shared(self) -> 'BuildFlags':
        self._shared = True
        return self
