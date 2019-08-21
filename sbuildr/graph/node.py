from sbuildr.tools import compiler, linker
from sbuildr.tools.flags import BuildFlags
from sbuildr.logger import G_LOGGER
from sbuildr.misc import paths

from typing import List
import copy
import os

# Represents a node in a dependency graph that tracks a path on the filesystem.
class Node(object):
    def __init__(self, path: str, inputs: List["Node"]=[]):
        self.path = path
        self.inputs: List[Node] = []
        self.outputs: List[Node] = []
        G_LOGGER.debug(f"Constructing Node with path: {self.path}, with {len(inputs)} inputs: {inputs}")
        for inp in inputs:
            self.add_input(inp)


    def timestamp_path(self) -> str:
        """
        The path to look at to determine the timestamp of this node.
        """
        return self.path


    def commands(self) -> List[List[str]]:
        """
        Commands that can be run to build this node.

        :returns: A list of commands, where each command is a list of strings.
        """
        return []


    def __str__(self):
        return f"{self.path}"

    def __repr__(self):
        return f"{self} (at {hex(id(self))})"

    # Returns a string representation of the dependency graph for this node.
    def dependency_graph_str(self, tab_depth=0):
        tab = '\t'
        out = f"{tab * tab_depth}{self.path}\n"
        for inp in self.inputs:
            out += f"{inp.dependency_graph_str(tab_depth + 1)}\n"
        return out

    # This function avoids duplicates
    def add_input(self, node: "Node"):
        if node not in self.inputs:
            G_LOGGER.verbose(f"Adding {self} as an output of {node}")
            node.outputs.append(self)
            self.inputs.append(node)

    def remove_input(self, node: "Node"):
        G_LOGGER.verbose(f"Removing {self} as an output of {node}")
        node.outputs.remove(self)
        self.inputs.remove(node)

class SourceNode(Node):
    def __init__(self, path: str, inputs: List["SourceNode"]=[], include_dirs: List[str]=None):
        super().__init__(path, inputs)
        # All include directories required for this file.
        self.include_dirs = include_dirs

class CompiledNode(Node):
    # These include_dirs are user-specified, since any scanned dirs would be in the SourceNode.
    def __init__(self, path: str, input: SourceNode, compiler: compiler.Compiler, include_dirs: List[str]=[], flags: BuildFlags=BuildFlags()):
        super().__init__(path, [input])
        self.compiler = compiler
        # All include directories required for this file.
        self.include_dirs = include_dirs
        self.flags = flags

    def add_input(self, node: SourceNode):
        if len(self.inputs) > 0:
            G_LOGGER.critical(f"Cannot create a CompiledNode with more than one source. This node already has one input: {self.inputs}")
        super().add_input(node)

    def commands(self) -> List[List[str]]:
        # The CompiledNode's include dirs take precedence over the SourceNode's. The ones in the SourceNode are
        # automatically deduced, whereas the ones in the CompiledNode are provided by the user.
        return [self.compiler.compile(self.inputs[0].path, self.path, self.include_dirs + self.inputs[0].include_dirs, self.flags)]

# Used to represent an external library. Project libraries are LinkedNodes
class Library(Node):
    # TODO: Add search_dirs parameter?
    def __init__(self, name: str=None, path: str=None, libs: List[str]=None, lib_dirs: List[str]=None):
        """
        Represents a library.

        :param name: The name of the library.
        :param path: A path to the library.
        :param libs: Names of libraries this library depends on.
        :param lib_dirs: A list of directories required for loading this library. This would generally include directories containing libraries that this library is linked against. For example, if the project requires ``liba``, and ``liba`` is linked against ``libb``, then ``lib_dirs`` should include the containing directory of ``libb``.

        Note that either a name or path must be provided. If a name is provided, then the containing directory for this library should be provided to ``lib_dirs``, unless it is in the default linker/loader search path.
        """
        if not (name or path):
            G_LOGGER.critical(f"Either a name or path must be provided to find a library")

        # TODO: FIXME: This will not handle non-standard library names (e.g. not in the form lib<name>.so)
        super().__init__(path)
        self.name = name or paths.libname_to_name(os.path.basename(self.path))
        self.libs = libs or [] # For handling python's silly default arguments
        self.lib_dirs = [os.path.abspath(dir) for dir in lib_dirs] if lib_dirs is not None else []

    def __str__(self):
        return f"{self.name}: {self.path} (lib_dirs: {self.lib_dirs})"

# Only CompiledNodes in the inputs list are passed on to the linker.
class LinkedNode(Library):
    def __init__(self, path: str, inputs: List[Node], linker: linker.Linker, internal_path: str, libs: List[str]=None, lib_dirs: List[str]=None, flags: BuildFlags=BuildFlags()):
        super().__init__(path=path, libs=libs, lib_dirs=lib_dirs)
        Node.__init__(self, path, inputs)
        # path is the externally visiable path, excluding linker signature.
        # internal path includes linker signature, so should be used for timestamping purposes.
        self.internal_path = internal_path
        self.linker = linker
        self.flags = flags


    def timestamp_path(self) -> str:
        return self.internal_path


    def commands(self) -> List[List[str]]:
        # Only link CompiledNodes. All libraries should come from self.libs
        return [self.linker.link([inp.path for inp in self.inputs if isinstance(inp, CompiledNode)], self.internal_path, self.libs, self.lib_dirs, self.flags)]


    def __str__(self):
        return Node.__str__(self)
