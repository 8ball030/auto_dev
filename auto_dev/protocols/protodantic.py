import re
import os
import sys
import inspect
import subprocess  # nosec: B404
from pathlib import Path
from types import ModuleType

from proto_schema_parser.parser import Parser
from jinja2 import Template, Environment, FileSystemLoader

from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER
from auto_dev.protocols.adapters import FileAdapter
from auto_dev.protocols import formatter, primitives as primitives_module


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


def _get_locally_defined_classes(module: ModuleType) -> list[type]:

    def locally_defined(obj):
        return isinstance(obj, type) and obj.__module__ == module.__name__

    return list(filter(locally_defined, vars(module).values()))


def create(
    proto_inpath: Path,
    code_outpath: Path,
    test_outpath: Path,
) -> None:

    repo_root = get_repo_root()
    env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa

    content = proto_inpath.read_text()

    primitives_py = repo_root / "auto_dev" / "protocols" / "primitives.py"
    protodantic_template = env.get_template('protocols/protodantic.jinja')
    hypothesis_template = env.get_template('protocols/hypothesis.jinja')

    primitives_outpath = code_outpath.parent / primitives_py.name
    primitives_outpath.write_text(primitives_py.read_text())

    models_import_path = _compute_import_path(code_outpath, repo_root)
    primitives_import_path = _compute_import_path(primitives_outpath, repo_root)

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

    custom_primitives = _get_locally_defined_classes(primitives_module)
    primitives = [cls for cls in custom_primitives if not inspect.isabstract(cls)]
    float_primitives = [p for p in primitives if issubclass(p, float)]
    integer_primitives = [p for p in primitives if issubclass(p, int)]

    file = FileAdapter.from_file(Parser().parse(content))

    code = generated_code = protodantic_template.render(
        file=file,
        formatter=formatter,
        float_primitives=float_primitives,
        integer_primitives=integer_primitives,
        primitives_import_path=primitives_import_path,
    )
    code_outpath.write_text(generated_code)

    pb2_path = code_outpath.parent / f"{proto_inpath.stem}_pb2.py"
    pb2_content = pb2_path.read_text()
    pb2_content = _remove_runtime_version_code(pb2_content)
    pb2_path.write_text(pb2_content)

    message_import_path = ".".join(models_import_path.split(".")[:-1]) or "."
    messages_pb2 = pb2_path.with_suffix("").name

    tests = generated_tests = hypothesis_template.render(
        file=file,
        float_primitives=float_primitives,
        integer_primitives=integer_primitives,
        primitives_import_path=primitives_import_path,
        models_import_path=models_import_path,
        message_import_path=message_import_path,
        messages_pb2=messages_pb2,
    )
    test_outpath.write_text(generated_tests)
