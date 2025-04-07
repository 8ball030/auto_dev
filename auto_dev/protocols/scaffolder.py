import tempfile
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from aea.protocols.generator.base import ProtocolGenerator

from auto_dev.utils import remove_prefix
from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER
from auto_dev.protocols import protodantic


class Metadata(BaseModel):
    """Metadata."""

    name: str
    author: str
    version: str
    description: str
    license: str
    aea_version: str
    protocol_specification_id: str
    speech_acts: dict[str, dict[str, str]] | None = None


class InteractionModel(BaseModel):
    """InteractionModel."""

    initiation: list[str]
    reply: dict[str, list[str]]
    termination: list[str]
    roles: dict[str, None]
    end_states: list[str]
    keep_terminal_state_dialogues: bool


class ProtocolSpecification(BaseModel):
    """ProtocolSpecification."""

    path: Path
    metadata: Metadata
    custom_definitions: dict[str, str] | None = None
    interaction_model: InteractionModel


def read_protocol_spec(filepath: str) -> ProtocolSpecification:
    """Read protocol specification."""

    content = Path(filepath).read_text(encoding=DEFAULT_ENCODING)

    # parse from README.md, otherwise we assume protocol.yaml
    if "```" in content:
        if content.count("```") != 2:
            msg = "Expecting a single code block"
            raise ValueError(msg)
        content = remove_prefix(content.split("```")[1], "yaml")

    # use ProtocolGenerator to validate the specification
    with tempfile.NamedTemporaryFile(mode="w", encoding=DEFAULT_ENCODING) as temp_file:
        Path(temp_file.name).write_text(content, encoding=DEFAULT_ENCODING)
        ProtocolGenerator(temp_file.name)

    content = list(yaml.safe_load_all(content))
    if len(content) == 3:
        metadata, custom_definitions, interaction_model = content
    elif len(content) == 2:
        metadata, interaction_model = content
        custom_definitions = None
    else:
        msg = f"Expected 2 or 3 YAML documents in {filepath}."
        raise ValueError(msg)

    return ProtocolSpecification(
        path=filepath,
        metadata=metadata,
        custom_definitions=custom_definitions,
        interaction_model=interaction_model,
    )


def protocol_scaffolder(protocol_specification_path: str, language, logger, verbose: bool = True):
    """Scaffolding protocol components.

    Args:
    ----
        protocol_specification_path: Path to the protocol specification file.
        language: Target language for the protocol.
        logger: Logger instance for output and debugging.
        verbose: Whether to enable verbose logging.

    """

    Path.cwd()
    protodantic.get_repo_root()
    env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa

    # 0. Read spec data
    read_protocol_spec(protocol_specification_path)
