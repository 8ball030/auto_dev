"""Connection scaffolder."""

import shutil
import sys
import tempfile
import textwrap
from collections import namedtuple
from pathlib import Path

import yaml
from aea import AEA_DIR
from aea.protocols.generator.base import ProtocolGenerator

from auto_dev.cli_executor import CommandExecutor
from auto_dev.constants import AEA_CONFIG, DEFAULT_ENCODING
from auto_dev.data.connections.template import CONNECTION_TEMPLATE
from auto_dev.data.connections.test_template import TEST_CONNECTION_TEMPLATE
from auto_dev.utils import folder_swapper, get_logger, remove_prefix

INDENT = "    "

ProtocolSpecification = namedtuple('ProtocolSpecification', ['metadata', 'custom_types', 'speech_acts'])


HANDLER_TEMPLATE = """
def {handler}(self, message: {protocol}Message, dialogue: {protocol}Dialogue) -> {protocol}Message:
    # TODO: implement necessary logic

    response_message = dialogue.reply(
        performative={protocol}Message.Performative.{performative},
        {kwargs},
    )

    return response_message
"""


def to_camel(name: str, sep="") -> str:
    """Snake to camelcase."""
    return sep.join(map(str.capitalize, name.split("_")))


def read_protocol(filepath: str) -> ProtocolSpecification:
    """Read protocol specification."""

    content = Path(filepath).read_text(encoding=DEFAULT_ENCODING)
    if "```" in content:
        if content.count("```") != 2:
            raise ValueError("Expecting a single code block")
        content = remove_prefix(content.split('```')[1], "yaml")

    # use ProtocolGenerator to validate the specification
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        Path(temp_file.name).write_text(content, encoding=DEFAULT_ENCODING)
        ProtocolGenerator(temp_file.name)

    metadata, custom_types, speech_acts = yaml.safe_load_all(content)
    return ProtocolSpecification(metadata, custom_types, speech_acts)


def get_handlers(protocol: ProtocolSpecification) -> str:
    """Format handler methods."""

    protocol_name = protocol.metadata["name"]
    speech_acts = protocol.metadata["speech_acts"]
    termination = set(protocol.speech_acts["termination"])
    reply = protocol.speech_acts["reply"]

    incoming_performatives = [a for a in speech_acts if a not in termination]
    performative_responses = {a: reply[a] for a in incoming_performatives}

    protocol = to_camel(protocol_name)
    methods = []
    for handler, replies in performative_responses.items():
        performative = replies[0]
        resp = speech_acts[performative]
        resp = ",\n".join(f"{kw}=..." for kw in resp)
        kwargs = textwrap.indent(resp, INDENT * 2).lstrip()
        methods += [
            HANDLER_TEMPLATE.format(
                handler=handler, protocol=protocol, performative=performative.upper(), kwargs=kwargs
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
    content = textwrap.indent(",\n".join(entries), INDENT * 1)
    handler_mapping = textwrap.indent("{\n" + content + ",\n}", INDENT * 2)

    return handler_mapping.lstrip()


class ConnectionFolderTemplate:  # pylint: disable=R0902  # Too many instance attributes
    """ConnectionFolderTemplate"""

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

    @property
    def kwargs(self) -> dict:
        """Template formatting kwargs."""

        protocol_name = self.protocol.metadata["name"]
        protocol_author = self.protocol.metadata["author"]
        speech_acts = list(self.protocol.metadata["speech_acts"])
        roles = list(self.protocol.speech_acts["roles"])

        handlers = get_handlers(self.protocol)
        handler_mapping = get_handler_mapping(self.protocol)

        kwargs = {
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

        return kwargs

    def augment(self) -> None:
        """(Over)write the connection files."""

        self.tests.mkdir()
        (self.tests / "__init__.py").touch()

        doc = "".join(part.format(**self.kwargs) + "\n" for part in CONNECTION_TEMPLATE)
        self.connection.write_text(doc)

        doc = "".join(part.format(**self.kwargs) + "\n" for part in TEST_CONNECTION_TEMPLATE)
        self.test_connection.write_text(doc)


class ConnectionScaffolder:
    """ConnectionScaffolder"""

    def __init__(self, name, protocol, logger, verbose: bool = True):
        """Initialize ConnectionScaffolder."""

        self.name = name
        self.logger = logger or get_logger()
        self.verbose = verbose
        self.protocol = read_protocol(protocol)
        self.logger.info(f"Read protocol specification: {protocol}")

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
