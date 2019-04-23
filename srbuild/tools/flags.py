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
        self._debug: bool = False
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

    def debug(self) -> 'BuildFlags':
        self._debug = True
        return self

    # Raw options, as a list of strings.
    # TODO(2): Split into xcompiler and xlinker
    def raw(self, opts: List[str]) -> 'BuildFlags':
        self._raw = opts
        return self

    # Overwrite self where needed.
    def __iadd__(self, other):
        self._o = other._o or self._o
        self._std = other._std or self._std
        self._march = other._march or self._march
        self._fpic = other._fpic or self._fpic
        self._shared = other._shared or self._shared
        self._raw += other._raw
        return self

    def __add__(self, other):
        tmp = copy.deepcopy(self)
        tmp += other
        return tmp
