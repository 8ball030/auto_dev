import re
import os
import subprocess  # nosec: B404
from pathlib import Path

from jinja2 import Template, Environment, FileSystemLoader
from proto_schema_parser.parser import Parser

from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER


FLOAT_PRIMITIVES = [
    "Double",
    "Float",
]

INTEGER_PRIMITIVES = [
    "Int32",
    "Int64",
    "UInt32",
    "UInt64",
    "SInt32",
    "SInt64",
    "Fixed32",
    "Fixed64",
    "SFixed32",
    "SFixed64",
]


def get_repo_root() -> Path:
    command = ["git", "rev-parse", "--show-toplevel"]
    repo_root = subprocess.check_output(command, stderr=subprocess.STDOUT).strip()  # nosec: B603
    return Path(repo_root.decode("utf-8"))


def _compute_import_path(file_path: Path, repo_root: Path) -> str:
    if file_path.is_relative_to(repo_root):
        relative_path = file_path.relative_to(repo_root)
        return ".".join(relative_path.with_suffix('').parts)
    return f".{file_path.stem}"


def _remove_runtime_version_code(pb2_content: str) -> str:
    pb2_content = re.sub(r'^from\s+google\.protobuf\s+import\s+runtime_version\s+as\s+_runtime_version\s*\n', '', pb2_content, flags=re.MULTILINE)
    pb2_content = re.sub(r'_runtime_version\.ValidateProtobufRuntimeVersion\s*\(\s*[^)]*\)\s*\n?', '', pb2_content, flags=re.DOTALL)
    return pb2_content


def create(
    proto_inpath: Path,
    code_outpath: Path,
    test_outpath: Path,
) -> None:

    repo_root = get_repo_root()
    env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa

    content = proto_inpath.read_text()

    primitives_template = env.get_template('protocols/primitives.jinja')
    protodantic_template = env.get_template('protocols/protodantic.jinja')
    hypothesis_template = env.get_template('protocols/hypothesis.jinja')

    primitives = primitives_template.render()
    primitives_outpath = code_outpath.parent / "primitives.py"
    primitives_outpath.write_text(primitives)
    primitives_import_path = _compute_import_path(primitives_outpath, repo_root)

    result = Parser().parse(content)
    code = generated_code = protodantic_template.render(
        result=result,
        float_primitives=FLOAT_PRIMITIVES,
        integer_primitives=INTEGER_PRIMITIVES,
        primitives_import_path=primitives_import_path,
    )
    code_outpath.write_text(generated_code)

    subprocess.run(
        [
            "protoc",
            f"--python_out={code_outpath.parent}",
            f"--proto_path={proto_inpath.parent}",
            proto_inpath.name,
        ],
        cwd=proto_inpath.parent,
        check=True
    )

    models_import_path = _compute_import_path(code_outpath, repo_root)
    message_path = str(Path(models_import_path).parent)

    pb2_path = code_outpath.parent / f"{proto_inpath.stem}_pb2.py"
    pb2_content = pb2_path.read_text()
    pb2_content = _remove_runtime_version_code(pb2_content)
    pb2_path.write_text(pb2_content)

    messages_pb2 = pb2_path.with_suffix("").name

    tests = generated_tests = hypothesis_template.render(
        result=result,
        float_primitives=FLOAT_PRIMITIVES,
        integer_primitives=INTEGER_PRIMITIVES,
        primitives_import_path=primitives_import_path,
        models_import_path=models_import_path,
        message_path=message_path,
        messages_pb2=messages_pb2,
    )
    test_outpath.write_text(generated_tests)
