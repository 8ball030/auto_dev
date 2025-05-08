"""Module for generating pydantic models and associated hypothesis tests."""

from __future__ import annotations

import re
import inspect
import subprocess  # nosec: B404
from typing import TYPE_CHECKING, Any
from pathlib import Path

from jinja2 import Template, Environment, FileSystemLoader
from pydantic import BaseModel, ConfigDict
from proto_schema_parser.parser import Parser

from auto_dev.constants import PKG_ROOT, JINJA_TEMPLATE_FOLDER
from auto_dev.protocols import formatter, primitives as primitives_module
from auto_dev.protocols.adapters import FileAdapter


if TYPE_CHECKING:
    from types import ModuleType


class JinjaTemplates(BaseModel, arbitrary_types_allowed=True):
    """JinjaTemplates."""

    primitive_strategies: Template
    protodantic: Template
    hypothesis: Template

    @classmethod
    def load(cls):
        """Load from jinja2.Environment."""
        env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa
        env.globals["formatter"] = formatter
        return cls(**{field: env.get_template(f"protocols/{field}.jinja") for field in cls.model_fields})


class ImportPaths(BaseModel):
    """ImportPaths."""

    strategies: str
    primitives: str
    models: str
    message: str

    @classmethod
    def from_paths(
        cls,
        *,
        repo_root: Path,
        strategies_outpath: Path,
        primitives_outpath: Path,
        code_outpath: Path,
    ) -> ImportPaths:
        """Determine necessary module paths from outpaths."""

        models_import_path = _compute_import_path(code_outpath, repo_root)
        return cls(
            strategies=_compute_import_path(strategies_outpath, repo_root),
            primitives=_compute_import_path(primitives_outpath, repo_root),
            models=models_import_path,
            message=".".join(models_import_path.split(".")[:-1]) or ".",
        )


class TemplateContext(BaseModel):
    """TemplateContext."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    file: Any
    float_primitives: list[type]
    integer_primitives: list[type]
    import_paths: ImportPaths
    messages_pb2: str

    def shallow_dump(self) -> dict[str, Any]:
        """Shallow dump pydantic model."""

        return {name: getattr(self, name) for name in self.model_fields}


def get_repo_root() -> Path:
    """Get repository root directory path."""

    command = ["git", "rev-parse", "--show-toplevel"]
    repo_root = subprocess.check_output(command, stderr=subprocess.STDOUT).strip()  # nosec: B603
    return Path(repo_root.decode("utf-8"))


def _compute_import_path(file_path: Path, repo_root: Path) -> str:
    if file_path.is_relative_to(repo_root):
        relative_path = file_path.relative_to(repo_root)
        return ".".join(relative_path.with_suffix("").parts)
    return f".{file_path.stem}"


def _remove_runtime_version_code(pb2_content: str) -> str:
    pb2_content = re.sub(
        r"^from\s+google\.protobuf\s+import\s+runtime_version\s+as\s+_runtime_version\s*\n",
        "",
        pb2_content,
        flags=re.MULTILINE,
    )
    return re.sub(
        r"_runtime_version\.ValidateProtobufRuntimeVersion\s*\(\s*[^)]*\)\s*\n?", "", pb2_content, flags=re.DOTALL
    )


def _get_locally_defined_classes(module: ModuleType) -> list[type]:
    def locally_defined(obj):
        return isinstance(obj, type) and obj.__module__ == module.__name__

    return list(filter(locally_defined, vars(module).values()))


def copy_primitives(pkg_root: Path, code_outpath: Path) -> Path:
    """Copy primitives."""
    primitives_py = pkg_root / "protocols" / "primitives.py"
    primitives_outpath = code_outpath.parent / primitives_py.name
    primitives_outpath.write_text(primitives_py.read_text())
    return primitives_outpath


def _run_protoc(proto_inpath: Path, code_outpath: Path) -> Path:
    subprocess.run(
        [
            "protoc",
            f"--python_out={code_outpath.parent}",
            f"--proto_path={proto_inpath.parent}",
            proto_inpath.name,
        ],
        cwd=proto_inpath.parent,
        check=True,
    )
    return code_outpath.parent / f"{proto_inpath.stem}_pb2.py"


def _extract_primitives(primitives_module) -> tuple[list[type], list[type]]:
    custom_primitives = _get_locally_defined_classes(primitives_module)
    primitives = [cls for cls in custom_primitives if not inspect.isabstract(cls)]
    float_primitives = [p for p in primitives if issubclass(p, float)]
    integer_primitives = [p for p in primitives if issubclass(p, int)]
    return float_primitives, integer_primitives


def _prepare_pb2(proto_inpath: Path, code_outpath: Path) -> Path:
    pb2_path = _run_protoc(proto_inpath, code_outpath)
    pb2_content = pb2_path.read_text()
    pb2_content = _remove_runtime_version_code(pb2_content)
    pb2_path.write_text(pb2_content)
    return pb2_path


def create(
    proto_inpath: Path,
    code_outpath: Path,
    test_outpath: Path,
) -> None:
    """Main function to create pydantic models from a .proto file."""

    repo_root = get_repo_root()
    jinja_templates = JinjaTemplates.load()

    # Copy primitives file
    primitives_outpath = copy_primitives(PKG_ROOT, code_outpath)

    # import the custom primitive types
    float_primitives, integer_primitives = _extract_primitives(primitives_module)

    # load the .proto file AST tree
    file = FileAdapter.from_file(Parser().parse(proto_inpath.read_text()))

    # Run protoc to generate pb2 file, then remove runtime imports
    pb2_path = _prepare_pb2(proto_inpath, code_outpath)

    # compute import paths
    strategies_outpath = test_outpath.parent / "primitive_strategies.py"

    # generate template context
    import_paths = ImportPaths.from_paths(
        repo_root=repo_root,
        strategies_outpath=strategies_outpath,
        primitives_outpath=primitives_outpath,
        code_outpath=code_outpath,
    )
    template_context = TemplateContext(
        file=file,
        float_primitives=float_primitives,
        integer_primitives=integer_primitives,
        import_paths=import_paths,
        messages_pb2=pb2_path.with_suffix("").name,
    )

    # render jinja templates
    jinja_kwargs = template_context.shallow_dump()

    generated_code = jinja_templates.protodantic.render(**jinja_kwargs)
    code_outpath.write_text(generated_code)

    generated_strategies = jinja_templates.primitive_strategies.render(**jinja_kwargs)
    strategies_outpath.write_text(generated_strategies)

    generated_tests = jinja_templates.hypothesis.render(**jinja_kwargs)
    test_outpath.write_text(generated_tests)
