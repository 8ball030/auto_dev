"""
Dialogues scaffolder.
"""

from enum import Enum

from jinja2 import Environment, FileSystemLoader

from auto_dev.utils import get_logger
from auto_dev.constants import JINJA_TEMPLATE_FOLDER
from auto_dev.behaviours.scaffolder import BehaviourScaffolder


class DialogueTypes(Enum):
    """Dialogue types enum."""

    simple = "simple"
    abci = "abci"


class DialogueScaffolder(BehaviourScaffolder):
    """Dialogue Scaffolder."""

    component_class: str = "dialogues"
    type: DialogueTypes = DialogueTypes.simple

    def __init__(
        self, protocol_specification_path: str, dialogue_type, logger, verbose: bool = True, auto_confirm: bool = False
    ):
        """Initialize ProtocolScaffolder."""
        self.logger = logger or get_logger()
        self.verbose = verbose
        self.behaviour_type = dialogue_type
        self.protocol_specification_path = protocol_specification_path
        self.logger.info(f"Read protocol specification: {protocol_specification_path}")
        self.auto_confirm = auto_confirm
        self.env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa
