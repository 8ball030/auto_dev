import tempfile
import subprocess
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from aea.protocols.generator.base import ProtocolGenerator

from auto_dev.utils import remove_prefix, snake_to_camel
from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER
from auto_dev.protocols import protodantic, performatives


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

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def author(self) -> str:
        return self.metadata.author

    @property
    def camel_name(self) -> str:
        return snake_to_camel(self.metadata.name)

    @property
    def custom_types(self) -> list[str]:
        return [custom_type.removeprefix("ct:") for custom_type in self.custom_definitions]

    @property
    def performative_types(self) -> dict[str, dict[str, str]]:
        performative_types = {}
        for performative, message_fields in self.metadata.speech_acts.items():
            field_types = {}
            for field_name, value_type in message_fields.items():
                field_types[field_name] = performatives.parse_annotation(value_type)
            performative_types[performative] = field_types
        return performative_types

    @property
    def initial_performative_types(self) -> dict[str, dict[str, str]]:
        return {k: v for k, v in self.performative_types.items() if k in self.interaction_model.initiation}

    @property
    def outpath(self) -> Path:
        return protodantic.get_repo_root() / "packages" / self.author / "protocols" / self.name

    @property
    def code_outpath(self) -> Path:
        return self.outpath / "custom_types.py"

    @property
    def test_outpath(self) -> Path:
        return self.outpath / "tests" / "test_custom_types.py"


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


def run_cli_cmd(command: list[str], cwd: Path | None = None):
    result = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd or Path.cwd(),
        )
    if result.returncode != 0:
        msg = f"Failed: {command}:\n{result.stderr}"
        raise ValueError(msg)


def initialize_packages(repo_root: Path) -> None:
    packages_dir = repo_root / "packages"
    if not packages_dir.exists():
        run_cli_cmd(["aea", "packages", "init"], cwd=repo_root)


def run_aea_generate_protocol(protocol_path: Path, language: str, agent_dir: Path) -> None:
    command = ["aea", "-s", "generate", "protocol", str(protocol_path), "--l", language]
    run_cli_cmd(command, cwd=agent_dir)


def run_aea_publish(agent_dir: Path) -> None:
    command = ["aea", "publish", "--local", "--push-missing"]
    run_cli_cmd(command, cwd=agent_dir)


def generate_readme(protocol, template):
    readme = protocol.outpath / "README.md"
    protocol_definition = Path(protocol.path).read_text(encoding="utf-8")
    content = template.render(
        name=" ".join(map(str.capitalize, protocol.name.split("_"))),
        description=protocol.metadata.description,
        protocol_definition=protocol_definition,
    )
    readme.write_text(content.strip())


def protocol_scaffolder(protocol_specification_path: str, language, logger, verbose: bool = True):
    """Scaffolding protocol components.

    Args:
    ----
        protocol_specification_path: Path to the protocol specification file.
        language: Target language for the protocol.
        logger: Logger instance for output and debugging.
        verbose: Whether to enable verbose logging.

    """

    agent_dir = Path.cwd()
    repo_root = protodantic.get_repo_root()
    env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa

    # 0. Read spec data
    protocol = read_protocol_spec(protocol_specification_path)

    # 1. initialize packages folder if non-existent
    initialize_packages(repo_root)

    # 2. AEA generate protocol
    run_aea_generate_protocol(protocol.path, language=language, agent_dir=agent_dir)

    # Ensures `protocol.outpath` exists, required for correct import path generation
    # TODO: on error during any part of this process, clean up (remove) `protocol.outpath`
    run_aea_publish(agent_dir)

    # 3. create README.md
    template = env.get_template("protocols/README.jinja")
    generate_readme(protocol, template)
