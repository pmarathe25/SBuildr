from sbuildr.project.project import Project
from sbuildr.project.profile import Profile
from sbuildr.tools.flags import BuildFlags
from sbuildr.tools import compiler, linker
from sbuildr.graph.node import Library
from sbuildr.logger import G_LOGGER, SBuildrException, Verbosity
__version__ = "0.5.0"

G_LOGGER.info(f"Loading SBuildr {__version__} from {__path__}")
