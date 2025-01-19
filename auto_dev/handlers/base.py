"""
Simple handler scaffolder to allow users to scaffold a new handler from a protocol specification.
"""

from enum import Enum

from jinja2 import Environment, FileSystemLoader

from auto_dev.utils import get_logger
from auto_dev.constants import JINJA_TEMPLATE_FOLDER
from auto_dev.behaviours.scaffolder import BehaviourScaffolder


class HandlerTypes(Enum):
    """Dialogue types enum."""

    simple = "simple"
    abci = "abci"
    open_api = "open_api"


class HandlerScaffolder(BehaviourScaffolder):
    """Handler Scaffolder."""

    component_class: str = "handlers"
    type: HandlerTypes = HandlerTypes.simple

    def __init__(
        self, protocol_specification_path: str, handler_type, logger, verbose: bool = True, auto_confirm: bool = False
    ):
        """Initialize ProtocolScaffolder."""
        self.logger = logger or get_logger()
        self.verbose = verbose
        self.behaviour_type = handler_type
        self.protocol_specification_path = protocol_specification_path
        self.logger.info(f"Read protocol specification: {protocol_specification_path}")
        self.auto_confirm = auto_confirm
        self.env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa
