import shutil
import tempfile
import subprocess
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from proto_schema_parser import ast
from proto_schema_parser.parser import Parser
from aea.protocols.generator.base import ProtocolGenerator
from proto_schema_parser.generator import Generator

from auto_dev.utils import file_swapper, remove_prefix, snake_to_camel
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


def generate_custom_types(protocol: ProtocolSpecification):
    """Generate custom_types.py and tests/test_custom_types.py."""

    proto_inpath = protocol.outpath / f"{protocol.name}.proto"
    file = Parser().parse(proto_inpath.read_text())

    # extract custom type messages from AEA framework "wrapper" message
    main_message = file.file_elements.pop(1)
    custom_type_names = {name.removeprefix("ct:") for name in protocol.custom_definitions}
    for element in main_message.elements:
        if isinstance(element, ast.Message) and element.name in custom_type_names:
            file.file_elements.append(element)

    proto = Generator().generate(file)
    tmp_proto_path = protocol.outpath / f"tmp_{proto_inpath.name}"
    tmp_proto_path.write_text(proto)

    proto_pb2 = protocol.outpath / f"{protocol.name}_pb2.py"
    backup_pb2 = proto_pb2.with_suffix(".bak")
    shutil.move(str(proto_pb2), str(backup_pb2))
    with file_swapper(proto_inpath, tmp_proto_path):
        protodantic.create(
            proto_inpath=proto_inpath,
            code_outpath=protocol.code_outpath,
            test_outpath=protocol.test_outpath,
        )
    shutil.move(str(backup_pb2), str(proto_pb2))
    pb2_content = proto_pb2.read_text()
    pb2_content = protodantic._remove_runtime_version_code(pb2_content)
    proto_pb2.write_text(pb2_content)
    tmp_proto_path.unlink()


def rewrite_test_custom_types(protocol: ProtocolSpecification) -> None:
    content = protocol.test_outpath.read_text()
    a = f"packages.{protocol.author}.protocols.{protocol.name} import {protocol.name}_pb2"
    b = f"packages.{protocol.author}.protocols.{protocol.name}.{protocol.name}_pb2 import {protocol.camel_name}Message as {protocol.name}_pb2  # noqa: N813"
    protocol.test_outpath.write_text(content.replace(a, b))


def generate_dialogues(protocol: ProtocolSpecification, template):
    """Generate dialogues.py."""

    valid_replies = protocol.interaction_model.reply
    roles = [{"name": r.upper(), "value": r} for r in protocol.interaction_model.roles]
    end_states = [{"name": s.upper(), "value": idx} for idx, s in enumerate(protocol.interaction_model.end_states)]
    keep_terminal = protocol.interaction_model.keep_terminal_state_dialogues

    output = template.render(
        header="# Auto-generated by tool",
        author=protocol.author,
        snake_name=protocol.name,
        camel_name=protocol.camel_name,
        initial_performatives=protocol.interaction_model.initiation,
        terminal_performatives=protocol.interaction_model.termination,
        valid_replies=valid_replies,
        roles=roles,
        role=roles[0]["name"],
        end_states=end_states,
        keep_terminal_state_dialogues=keep_terminal,
    )
    dialogues = protocol.outpath / "dialogues.py"
    dialogues.write_text(output)


def generate_tests_init(protocol: ProtocolSpecification) -> None:
    test_init_file = protocol.outpath / "tests" / "__init__.py"
    test_init_file.write_text(f'"""Test module for the {protocol.name}"""')


def generate_test_dialogues(protocol: ProtocolSpecification, template) -> None:
    output = template.render(
        header="# Auto-generated by tool",
        author=protocol.author,
        snake_name=protocol.name,
        camel_name=protocol.camel_name,
        initial_performative_types=protocol.initial_performative_types,
        custom_types=protocol.custom_types,
        snake_to_camel=snake_to_camel,
    )
    test_dialogues = protocol.outpath / "tests" / f"test_{protocol.name}_dialogues.py"
    test_dialogues.write_text(output)


def generate_test_messages(protocol: ProtocolSpecification, template) -> None:
    output = template.render(
        header="# Auto-generated by tool",
        author=protocol.author,
        snake_name=protocol.name,
        camel_name=protocol.camel_name,
        performative_types=protocol.performative_types,
        custom_types=protocol.custom_types,
        snake_to_camel=snake_to_camel,
    )
    test_messages = protocol.outpath / "tests" / f"test_{protocol.name}_messages.py"
    test_messages.write_text(output)


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

    # 4. Generate custom_types.py and test_custom_types.py
    generate_custom_types(protocol)

    # 5. rewrite test_custom_types to patch the import
    rewrite_test_custom_types(protocol)

    # 6. Dialogues
    template = env.get_template("protocols/dialogues.jinja")
    generate_dialogues(protocol, template)

    # 7. generate __init__.py in tests folder
    generate_tests_init(protocol)

    # 8. Test dialogues
    template = env.get_template("protocols/test_dialogues.jinja")
    generate_test_dialogues(protocol, template)

    # 9. Test messages
    template = env.get_template("protocols/test_messages.jinja")
    generate_test_messages(protocol, template)
