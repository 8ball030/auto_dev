import re
import os
import subprocess  # nosec: B404
from pathlib import Path
from pprint import pprint
from collections import defaultdict

from typing import Union
from typing import Generic, TypeVar
from jinja2 import Template, Environment, FileSystemLoader
from pydantic import BaseModel

from hypothesis import strategies as st

from proto_schema_parser.parser import Parser
from proto_schema_parser.ast import Message, Enum, OneOf, Field

from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER


def get_repo_root() -> Path:
    command = ["git", "rev-parse", "--show-toplevel"]
    repo_root = subprocess.check_output(command, stderr=subprocess.STDOUT).strip()  # nosec: B603
    return Path(repo_root.decode("utf-8"))


def _compute_import_path(file_path: Path, repo_root: Path) -> str:
    if file_path.is_relative_to(repo_root):
        relative_path = file_path.relative_to(repo_root)
        return ".".join(relative_path.with_suffix('').parts)
    return f".{file_path.stem}"


def create(
    proto_inpath: Path,
    code_outpath: Path,
    test_outpath: Path,
) -> None:

    repo_root = get_repo_root()
    env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa

    content = proto_inpath.read_text()

    protodantic_template = env.get_template('protocols/protodantic.jinja')
    hypothesis_template = env.get_template('protocols/hypothesis.jinja')

    result = Parser().parse(content)
    generated_code = protodantic_template.render(result=result)
    code_outpath.write_text(generated_code)

    import_path = _compute_import_path(code_outpath, test_outpath)
    generated_tests = hypothesis_template.render(result=result, import_path=import_path)
    test_outpath.write_text(generated_tests)
