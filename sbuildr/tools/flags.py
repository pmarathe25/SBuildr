from sbuildr.logger import G_LOGGER
from typing import Union, List
import enum
import copy

# This is required to make the build system truly platform-agnostic.
# The same high-level options should work everywhere.
class BuildFlags(object):
    """
    Abstract description of compiler and linker flags. These are interpreted by SBuildr's compiler and linker interfaces and converted to concrete command-line flags.

    It is possible to add two BuildFlags, in which case the right-hand side takes precedence when flags are set for both instances. For example,
    ``BuildFlags.O(3).fpic() + BuildFlags.O(0)``
    would result in a value equivalent to:
    ``BuildFlags.O(0).fpic()``
    """
    def __init__(self):
        self._o: str = None
        self._std: str = None
        self._march: str = None
        self._fpic: bool = None
        # Distinguishes shared library from executable.
        self._shared: bool = None
        self._debug: bool = None
        self._defines: Set[str] = set()
        self._raw: List[str] = []

    # Internal only, should not need to be called by the user.
    def _enable_shared(self) -> 'BuildFlags':
        self._shared = True
        return self

    def O(self, level: Union[int, str]) -> 'BuildFlags':
        """
        Sets the optimization level.

        :param level: An integer or string indicating the optimization level. For example, to disable optimization, this would be set to ``0`` or ``"0"``.

        :returns: self
        """
        self._o = str(level).strip()
        return self

    def std(self, year: Union[int, str]) -> 'BuildFlags':
        """
        Sets the C++ standard.

        :param year: An integer or string indicating the last two digits of the year of the corresponding C++ standard. For example, to use C++11, this would be set to ``11`` or ``"11"``.

        :returns: self
        """
        self._std = str(year).strip()
        return self

    def march(self, type: str) -> 'BuildFlags':
        """
        Sets the microarchitecture.

        :param type: A string describing the CPU microarchitecture.

        :returns: self
        """
        self._march = str(type).strip()
        return self

    def fpic(self, use=True) -> 'BuildFlags':
        """
        Enables or disables generation of position independent code.

        :param use: Whether to generate position independent code.

        :returns: self
        """
        self._fpic = use
        return self

    def debug(self, use=True) -> 'BuildFlags':
        """
        Enables or disables generation of debug information.

        :param use: Whether to generate debug information.

        :returns: self
        """
        self._debug = use
        return self

    def define(self, macro) -> 'BuildFlags':
        """
        Defines the specified macro during compilation. This can be useful to enable/disable code paths using #ifdefs.

        :param macro: The macro to define.

        :returns: self
        """
        self._defines.add(str(macro))
        return self

    # Raw options, as a list of strings.
    # TODO(2): Split into xcompiler and xlinker
    def raw(self, opts: List[str]) -> 'BuildFlags':
        """
        Allows for providing raw options.

        :param opts: A list of options, as strings. These are passed on to the compiler and linker without modification.

        :returns: self
        """
        self._raw = opts
        return self

    # Overwrite self where needed.
    def __iadd__(self, other):
        self._o = other._o if other._o is not None else self._o
        self._std = other._std if other._std is not None else self._std
        self._march = other._march if other._march is not None else self._march
        self._fpic = other._fpic if other._fpic is not None else self._fpic
        self._shared = other._shared if other._shared is not None else self._shared
        self._defines |= other._defines
        self._raw += other._raw
        return self

    def __add__(self, other):
        tmp = copy.deepcopy(self)
        tmp += other
        return tmp
