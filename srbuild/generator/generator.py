from srbuild.graph.node import Node, SourceNode, CompiledNode, LinkedNode
from srbuild.logger import G_LOGGER
from typing import List

class Generator(object):
    # Generate a build command for the given node.
    # For source nodes and basic nodes this is an empty list, otherwise, it is a compiler/linker command.
    def _build_command(self, node: Node) -> List[str]:
        if isinstance(node, CompiledNode):
            if len(node.inputs) != 1:
                G_LOGGER.critical(f"CompiledNodes must have exactly one inputs, but received {node} with inputs: {node.inputs}")
            source = node.inputs[0]
            # The CompiledNode's include dirs take precedence over the SourceNode's. The ones in the SourceNode are
            # automatically deduced, whereas the ones in the CompiledNode are provided by the user.
            return node.compiler.compile(source.path, node.path, node.include_dirs + source.include_dirs, node.flags)
        elif isinstance(node, LinkedNode):
            return node.linker.link([inp.path for inp in node.inputs], node.path, node.libs, node.lib_dirs, node.flags)
        return []
