import re
import subprocess  # nosec: B404
from pathlib import Path
from pprint import pprint
from collections import defaultdict

from typing import Union
from typing import Generic, TypeVar
from jinja2 import Template, Environment, FileSystemLoader
from pydantic import BaseModel
from pydantic.generics import GenericModel

from hypothesis import strategies as st

from proto_schema_parser.parser import Parser
from proto_schema_parser.ast import Message, Enum, OneOf, Field

from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER


def get_repo_root() -> Path:
    command = ["git", "rev-parse", "--show-toplevel"]
    repo_root = subprocess.check_output(command, stderr=subprocess.STDOUT).strip()  # nosec: B603
    return Path(repo_root.decode("utf-8"))


path = get_repo_root() / "tests" / "data" / "protocols" / "protobuf"
assert path.exists()
proto_files = {file.name: file for file in path.glob("*.proto")}

env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa
jinja_template = env.get_template('protocols/protodantic.jinja')

file = proto_files["primitives.proto"]
content = file.read_text()

result = Parser().parse(content)
generated_code = jinja_template.render(result=result)
print(generated_code)
