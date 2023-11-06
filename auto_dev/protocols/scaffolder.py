"""Protocol scaffolder."""

import subprocess
import tempfile
from collections import namedtuple
from pathlib import Path

import yaml
from aea.protocols.generator.base import ProtocolGenerator

from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.utils import get_logger, remove_prefix

ProtocolSpecification = namedtuple('ProtocolSpecification', ['metadata', 'custom_types', 'speech_acts'])


README_TEMPLATE = """
# {name} Protocol

## Description

...

## Specification

```yaml
{protocol_definition}
```
"""


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


class ProtocolScaffolder:
    """ProtocolScaffolder"""

    def __init__(self, protocol_specification_path: str, language, logger, verbose: bool = True):
        """Initialize ProtocolScaffolder."""

        self.logger = logger or get_logger()
        self.verbose = verbose
        self.language = language
        self.protocol_specification_path = protocol_specification_path
        self.logger.info(f"Read protocol specification: {protocol_specification_path}")

    def generate(self) -> None:
        """Generate protocol."""

        command = f"aea generate protocol {self.protocol_specification_path} --l {self.language}"
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if not result.returncode == 0:
            raise ValueError(f"Protocol scaffolding failed: {result.stderr}")

        protocol = read_protocol(self.protocol_specification_path)
        protocol_name = protocol.metadata["name"]
        protocol_path = Path.cwd() / "protocols" / protocol_name
        readme = protocol_path / "README.md"
        protocol_definition = Path(self.protocol_specification_path).read_text(encoding=DEFAULT_ENCODING)
        kwargs = {
            "name": " ".join(map(str.capitalize, protocol_name.split("_"))),
            "protocol_definition": protocol_definition,
        }
        content = README_TEMPLATE.format(**kwargs)
        readme.write_text(content.strip(), encoding=DEFAULT_ENCODING)

        connection_path = Path.cwd() / "protocols" / protocol_name
        self.logger.info(f"New protocol scaffolded at {connection_path}")
