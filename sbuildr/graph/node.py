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
        self.basename = os.path.basename(path) if path else None
        self.inputs: List[Node] = []
        self.outputs: List[Node] = []
        G_LOGGER.debug(f"Constructing Node with path: {self.path}, basename: {self.basename} with {len(inputs)} inputs: {inputs}")
        for inp in inputs:
            self.add_input(inp)

    def __str__(self):
        return f"{self.basename}: {self.path}"

    def __repr__(self):
        return f"{self} (at {hex(id(self))})"

    # Returns a string representation of the dependency graph for this node.
    def dependency_graph_str(self, tab_depth=0):
        tab = '\t'
        out = f"{tab * tab_depth}{self.basename}\n"
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

class Library(Node):
    # TODO: Add search_dirs parameter?
    def __init__(self, name: str=None, path: str=None, ld_dirs: List[str]=[]):
        """
        Represents a library.

        :param name: The name of the library.
        :param path: A path to the library.
        :param ld_dirs: A list of directories required for loading this library. This would generally include directories containing libraries that this library is linked against. For example, if the project requires ``liba``, and ``liba`` is linked against ``libb``, then ``ld_dirs`` should include the containing directory of ``libb``.

        Note that either a name or path must be provided. If a name is provided, then the containing directory for this library should be provided to ``ld_dirs``, unless it is in the default linker/loader search path.
        """
        if not (name or path):
            G_LOGGER.critical(f"Either a name or path must be provided to find a library")

        # TODO: FIXME: This will not handle non-standard library names (e.g. not in the form lib<name>.so)
        super().__init__(path)
        self.name = name or paths.libname_to_name(os.path.basename(self.path))
        self.ld_dirs = [os.path.abspath(dir) for dir in ld_dirs]
        if self.path:
            self.ld_dirs.insert(0, os.path.dirname(self.path))

    def __str__(self):
        return f"{self.name}"

# Only CompiledNodes in the inputs list are passed on to the linker.
class LinkedNode(Library):
    def __init__(self, path: str, inputs: List[Node], linker: linker.Linker, libs: List[str]=[], lib_dirs: List[str]=[], flags: BuildFlags=BuildFlags()):
        super().__init__(path=path, ld_dirs=lib_dirs)
        Node.__init__(self, path, inputs)
        self.linker = linker
        # Need a copy here because default arguments are silly in Python.
        self.libs = copy.deepcopy(libs)
        self.lib_dirs = lib_dirs
        self.flags = flags

    def __str__(self):
        return Node.__str__(self)
