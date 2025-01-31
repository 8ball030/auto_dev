"""Runner service package."""

from .runner import DevAgentRunner
from .prod_runner import ProdAgentRunner


DevAgentRunner = DevAgentRunner
ProdAgentRunner = ProdAgentRunner
