"""Connection scaffolder."""

import sys
import shutil
import tempfile
import textwrap
from pathlib import Path

import yaml
import rich_click as click
from aea import AEA_DIR
from aea.helpers.yaml_utils import yaml_dump
from aea.configurations.data_types import PublicId

from auto_dev.enums import FileType
from auto_dev.utils import get_logger, write_to_file, folder_swapper
from auto_dev.constants import AEA_CONFIG, DEFAULT_ENCODING
from auto_dev.cli_executor import CommandExecutor
from auto_dev.protocols.scaffolder import ProtocolSpecification, read_protocol
from auto_dev.data.connections.template import HEADER, CONNECTION_TEMPLATE
from auto_dev.data.connections.test_template import TEST_CONNECTION_TEMPLATE


INDENT = "    "

README_TEMPLATE = """
# {name} Connection

## Description

...
"""

REPLY_TEMPLATE = """
    response_message = dialogue.reply(
        performative={protocol}Message.Performative.{performative},
        {kwargs},
    )
"""

HANDLER_TEMPLATE = """
def {handler}(self, message: {protocol}Message, dialogue: {protocol}Dialogue) -> {protocol}Message:
    \"\"\"Handle {protocol}Message with {perfomative} Perfomative \"\"\"

    {message_content}

    # TODO: Implement the necessary logic required for the response message
    {replies}
    return response_message
"""


def to_camel(name: str, sep="") -> str:
    """Snake to camelcase."""
    return sep.join(map(str.capitalize, name.split("_")))


def _format_reply_content(protocol_name, speech_acts, responses):
    replies = []
    for response in responses:
        resp = ",\n".join(f"{kw}=..." for kw in speech_acts[response])
        kwargs = textwrap.indent(resp, INDENT * 2).lstrip()
        reply = REPLY_TEMPLATE.format(
            protocol=protocol_name,
            performative=response.upper(),
            kwargs=kwargs,
        )
        replies.append(reply)
    return "".join(replies)


def get_handlers(protocol: ProtocolSpecification) -> str:
    """Format handler methods."""
    speech_acts = protocol.metadata["speech_acts"]
    termination = set(protocol.speech_acts["termination"])
    reply = protocol.speech_acts["reply"]

    incoming_performatives = [a for a in speech_acts if a not in termination]
    performative_responses = {a: reply[a] for a in incoming_performatives}

    protocol_name = to_camel(protocol.metadata["name"])
    methods = []

    for performative, responses in performative_responses.items():
        incoming = "\n".join(f"{x} = message.{x}" for x in speech_acts[performative])
        message_content = textwrap.indent(incoming, INDENT).lstrip()
        replies = _format_reply_content(protocol_name, speech_acts, responses)
        methods += [
            HANDLER_TEMPLATE.format(
                handler=performative,
                protocol=protocol_name,
                perfomative=performative.upper(),
                message_content=message_content,
                replies=replies,
            )
        ]

    handlers = "".join(textwrap.indent(m, INDENT) for m in methods)
    return handlers.strip()


def get_handler_mapping(protocol: ProtocolSpecification) -> str:
    """Format mapping from performative to handler method."""
    protocol_name = protocol.metadata["name"]
    speech_acts = list(protocol.metadata["speech_acts"])
    termination = set(protocol.speech_acts["termination"])
    performatives = [a for a in speech_acts if a not in termination]

    name = to_camel(protocol_name)
    entry = "{name}Message.Performative.{performative}: self.{handler}"
    entries = (entry.format(name=name, performative=p.upper(), handler=p) for p in performatives)
    content = textwrap.indent(",\n".join(entries), INDENT)
    handler_mapping = textwrap.indent("{\n" + content + ",\n}", INDENT * 2)

    return handler_mapping.lstrip()


class ConnectionFolderTemplate:  # pylint: disable=R0902  # Too many instance attributes
    """ConnectionFolderTemplate."""

    def __init__(self, name: str, logger, protocol):
        self.name = name
        self.logger = logger
        self.src = Path(AEA_DIR) / "connections" / "scaffold"
        self.path = Path(tempfile.mkdtemp()) / "scaffold"
        self.protocol = protocol
        shutil.copytree(self.src, self.path)

        self.readme = (self.path / "readme.md").read_text()
        self.connection = self.path / "connection.py"
        self.yaml = yaml.safe_load_all(self.path / "connection.yaml")
        self.tests = self.path / "tests"
        self.test_connection = self.tests / "test_connection.py"
        self.test_connection_init = self.tests / "__init__.py"

    @property
    def kwargs(self) -> dict:
        """Template formatting kwargs."""
        protocol_name = self.protocol.metadata["name"]
        protocol_author = self.protocol.metadata["author"]
        speech_acts = list(self.protocol.metadata["speech_acts"])
        roles = list(self.protocol.speech_acts["roles"])

        handlers = get_handlers(self.protocol)
        handler_mapping = get_handler_mapping(self.protocol)

        return {
            "year": 2023,  # overwritten by aea scaffold
            "author": AEA_CONFIG["author"],  # overwritten by aea scaffold in copyright header
            "name": self.name,
            "name_camelcase": to_camel(self.name),
            "proper_name": to_camel(self.name, sep=" "),
            "protocol_author": protocol_author,
            "protocol_name": protocol_name,
            "protocol_name_camelcase": to_camel(protocol_name),
            "handlers": handlers,
            "handler_mapping": handler_mapping,
            "ROLE": roles[0].upper(),
            "OTHER_ROLE": roles[-1].upper(),
            "PERFORMATIVE": speech_acts[0].upper(),
        }

    def augment(self) -> None:
        """(Over)write the connection files."""
        self.tests.mkdir()

        doc = "".join(part.format(**self.kwargs) + "\n" for part in CONNECTION_TEMPLATE)
        self.connection.write_text(doc)

        doc = "".join(part.format(**self.kwargs) + "\n" for part in TEST_CONNECTION_TEMPLATE)
        self.test_connection.write_text(doc)

        doc = "".join(part.format(**self.kwargs) + "\n" for part in HEADER)
        self.test_connection_init = self.tests / "__init__.py"
        self.test_connection_init.write_text(doc)


class ConnectionScaffolder:
    """ConnectionScaffolder."""

    def __init__(self, ctx: click.Context, name: str, protocol_id: PublicId):
        """Initialize ConnectionScaffolder."""
        # `aea add protocol`, currently works only with `adev scaffold protocol crud_protocol.yaml`
        protocol_specification_path = Path("protocols") / protocol_id.name / "README.md"
        if not protocol_specification_path.exists():
            msg = f"{protocol_specification_path} not found. Checking vendor..."
            click.secho(msg, fg="yellow")
            protocol_specification_path = (
                Path("vendor") / protocol_id.author / "protocols" / protocol_id.name / "README.md"
            )
            if not protocol_specification_path.exists():
                msg = f"{protocol_specification_path} not found."
                raise click.ClickException(msg)

        self.ctx = ctx
        self.name = name
        self.logger = ctx.obj["LOGGER"] or get_logger()
        self.verbose = ctx.obj["VERBOSE"]
        self.protocol_id = protocol_id
        self.protocol = read_protocol(protocol_specification_path)
        self.logger.info(f"Read protocol specification: {protocol_specification_path}")

    def update_config(self) -> None:
        """Update connection.yaml."""
        connection_path = Path.cwd() / "connections" / self.name
        connection_yaml = connection_path / "connection.yaml"
        with open(connection_yaml, encoding=DEFAULT_ENCODING) as infile:
            connection_config = self.ctx.aea_ctx.connection_loader.load(infile)
        connection_config.protocols.add(self.protocol_id)
        connection_config.class_name = f"{to_camel(self.name)}Connection"
        connection_config.description = self.protocol.metadata["description"].replace("protocol", "connection")
        with open(connection_yaml, "w", encoding=DEFAULT_ENCODING) as outfile:  # # pylint: disable=R1732
            yaml_dump(connection_config.ordered_json, outfile)
        self.logger.info(f"Updated {connection_yaml}")

    def update_readme(self) -> None:
        """Update README.md."""
        connection_path = Path.cwd() / "connections" / self.name
        file_path = connection_path / "README.md"
        kwargs = {
            "name": " ".join(map(str.capitalize, self.name.split("_"))),
        }
        content = README_TEMPLATE.format(**kwargs)
        write_to_file(str(file_path), content, FileType.TEXT)

    def generate(self) -> None:
        """Generate connection."""
        template = ConnectionFolderTemplate(self.name, self.logger, self.protocol)
        template.augment()

        with folder_swapper(template.path, template.src):
            command = f"aea scaffold connection {self.name}"
            cli_executor = CommandExecutor(command.split(" "))
            result = cli_executor.execute(verbose=self.verbose)
            if not result:
                self.logger.error(f"Command failed: {command}")
                sys.exit(1)

        self.update_config()
        self.update_readme()

        connection_id = PublicId(AEA_CONFIG["author"], self.name, "0.1.0")
        cli_executor = CommandExecutor(f"aea fingerprint connection {connection_id}".split())
        result = cli_executor.execute(verbose=True)
        if not result:
            msg = f"Fingerprinting failed: {connection_id}"
            raise ValueError(msg)
