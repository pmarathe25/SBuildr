from srbuild.logger import G_LOGGER
from typing import Union, List
import enum
import copy

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
        self._raw: List[str] = []

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

    # Raw options, as a list of strings.
    def raw(self, opts: List[str]) -> 'BuildFlags':
        self._raw = opts
        return self

    def __iadd__(self, other):
        self._o = self._o or other._o
        self._std = self._std or other._std
        self._march = self._march or other._march
        self._fpic = self._fpic or other._fpic
        self._shared = self._shared or other._shared
        self._raw += other._raw
        return self

    def __add__(self, other):
        tmp = copy.deepcopy(self)
        tmp += other
        return tmp
