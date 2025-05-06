"""Module for generating protocols from a protocol.yaml specification."""

import re
import ast as pyast
import shutil
import inspect
import tempfile
import importlib
import subprocess
from enum import IntEnum
from pathlib import Path
from functools import cached_property
from collections.abc import Callable

import yaml
from jinja2 import Template, Environment, FileSystemLoader
from pydantic import BaseModel, ConfigDict
from proto_schema_parser import ast
from proto_schema_parser.parser import Parser
from aea.protocols.generator.base import ProtocolGenerator
from proto_schema_parser.generator import Generator

from auto_dev.utils import file_swapper, remove_prefix, camel_to_snake, snake_to_camel
from auto_dev.constants import DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER
from auto_dev.protocols import protodantic, performatives


CUSTOM_TYPE_COMMENT = """
# ruff: noqa: N806, C901, PLR0912, PLR0914, PLR0915, A001, UP007
# N806     - variable should be lowercase
# C901     - function is too complex
# PLR0912  - too many branches
# PLR0914  - too many local variables
# PLR0915  - too many statements
# A001     - shadowing builtin names like `id` and `type`
# UP007    - Use X | Y for type annotations  # NOTE: important edge case pydantic-hypothesis interaction!
"""


FLAT_ENUM_TEMPLATE = """
class {name}(IntEnum):
    \"\"\"{name}\"\"\"
    {clean_members}

    @staticmethod
    def encode(pb_obj, {snake_name}: {name}) -> None:
        \"\"\"Encode {name} to protobuf.\"\"\"
        pb_obj.{snake_name} = {snake_name}

    @classmethod
    def decode(cls, pb_obj) -> {name}:
        \"\"\"Decode protobuf to {name}.\"\"\"
        return cls(pb_obj.{snake_name})
"""


class JinjaTemplates(BaseModel, arbitrary_types_allowed=True):
    """JinjaTemplates."""

    README: Template
    dialogues: Template
    performatives: Template
    primitive_strategies: Template
    test_dialogues: Template
    test_messages: Template

    @classmethod
    def load(cls):
        """Load from jinja2.Environment."""
        env = Environment(loader=FileSystemLoader(JINJA_TEMPLATE_FOLDER), autoescape=False)  # noqa
        return cls(**{field: env.get_template(f"protocols/{field}.jinja") for field in cls.model_fields})


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


class TemplateContext(BaseModel):
    """TemplateContext."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    header: str
    description: str
    protocol_definition: str

    author: str
    name: str
    snake_name: str
    camel_name: str

    custom_types: list[str]
    initial_performatives: list[str]
    terminal_performatives: list[str]
    valid_replies: dict[str, list[str]]
    performative_types: dict[str, dict[str, str]]

    role: str
    roles: list[dict[str, str]]
    end_states: list[dict[str, str | int]]
    keep_terminal_state_dialogues: bool
    snake_to_camel: Callable[[str], str]


class ProtocolSpecification(BaseModel):
    """ProtocolSpecification."""

    path: Path
    metadata: Metadata
    custom_definitions: dict[str, str] | None = None
    interaction_model: InteractionModel

    @property
    def name(self) -> str:
        """Protocol name."""
        return self.metadata.name

    @property
    def author(self) -> str:
        """Protocol author."""
        return self.metadata.author

    @property
    def camel_name(self) -> str:
        """Protocol name in camel case."""
        return snake_to_camel(self.metadata.name)

    @property
    def custom_types(self) -> list[str]:
        """Top-level custom type names in protocol specification."""
        return [custom_type.removeprefix("ct:") for custom_type in self.custom_definitions]

    @property
    def performative_types(self) -> dict[str, dict[str, str]]:
        """Python type annotation for performatives."""

        performative_types = {}
        for performative, message_fields in self.metadata.speech_acts.items():
            field_types = {}
            for field_name, value_type in message_fields.items():
                field_types[field_name] = performatives.parse_annotation(value_type)
            performative_types[performative] = field_types
        return performative_types

    @property
    def outpath(self) -> Path:
        """Protocol expected outpath after `aea create` and `aea publish --local`."""
        return protodantic.get_repo_root() / "packages" / self.author / "protocols" / self.name

    @property
    def code_outpath(self) -> Path:
        """Outpath for custom_types.py."""
        return self.outpath / "custom_types.py"

    @property
    def test_outpath(self) -> Path:
        """Outpath for tests/test_custom_types.py."""
        return self.outpath / "tests" / "test_custom_types.py"

    @cached_property
    def template_context(self) -> TemplateContext:
        """Get the template context for template rendering."""

        roles = [{"name": r.upper(), "value": r} for r in self.interaction_model.roles]
        end_states = [{"name": s.upper(), "value": idx} for idx, s in enumerate(self.interaction_model.end_states)]
        protocol_definition = Path(self.path).read_text(encoding="utf-8")

        return TemplateContext(
            header="# Auto-generated by tool",
            description=self.metadata.description,
            protocol_definition=protocol_definition,
            author=self.metadata.author,
            name=" ".join(map(str.capitalize, self.name.split("_"))),
            snake_name=self.metadata.name,
            camel_name=snake_to_camel(self.metadata.name),
            custom_types=self.custom_types,
            initial_performatives=self.interaction_model.initiation,
            terminal_performatives=self.interaction_model.termination,
            valid_replies=self.interaction_model.reply,
            performative_types=self.performative_types,
            role=roles[0]["name"],
            roles=roles,
            end_states=end_states,
            keep_terminal_state_dialogues=self.interaction_model.keep_terminal_state_dialogues,
            snake_to_camel=snake_to_camel,
        )


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
    """Run CLI command helper function."""

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


def run_aea_generate_protocol(protocol_path: Path, language: str, agent_dir: Path) -> None:
    """Run `aea generate protocol`."""
    command = ["aea", "-s", "generate", "protocol", str(protocol_path), "--l", language]
    run_cli_cmd(command, cwd=agent_dir)


def run_push_local_protocol(protocol: ProtocolSpecification, agent_dir: Path) -> None:
    """Run `aea push --local protocol`."""
    command = ["aea", "push", "--local", "protocol", protocol.metadata.protocol_specification_id]
    run_cli_cmd(command, cwd=agent_dir)


def generate_readme(protocol, template):
    """Generate protocol README.md file."""
    readme = protocol.outpath / "README.md"
    Path(protocol.path).read_text(encoding="utf-8")
    content = template.render(**protocol.template_context.model_dump())
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
    pb2_content = protodantic._remove_runtime_version_code(pb2_content)  # noqa: SLF001
    proto_pb2.write_text(pb2_content)
    tmp_proto_path.unlink()


def post_enum_processing(protocol: ProtocolSpecification):
    """AST-based in-place flattening of enum-only message classes."""

    # Dynamically import the generated models to detect enum-only message classes
    spec = importlib.util.spec_from_file_location("generated_models", protocol.code_outpath)
    models_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_mod)

    def is_enum_only_model(cls: type[BaseModel]) -> bool:
        nested = [member for _, member in inspect.getmembers(cls, inspect.isclass) if issubclass(member, IntEnum)]
        fields = list(cls.model_fields)
        return len(nested) == 1 and len(fields) == 1

    def inject_comment(src: str, comment: str) -> str:
        # Matches the whole leading import block (one or more import lines + trailing blank lines)
        pattern = re.compile(r"^((?:(?:import|from)\s.*\n)+\n*)", re.MULTILINE)
        replacement = r"\1" + comment.rstrip() + "\n\n"
        return pattern.sub(replacement, src, count=1)

    enum_only_names = {
        name
        for name, cls in inspect.getmembers(models_mod, inspect.isclass)
        if cls.__module__ == models_mod.__name__ and issubclass(cls, BaseModel) and is_enum_only_model(cls)
    }

    # Pre-generate flat enum class source snippets
    flat_src_map: dict[str, str] = {}
    for name in enum_only_names:
        snake_name = camel_to_snake(name)
        cls = getattr(models_mod, name)
        enum = next(member for _, member in inspect.getmembers(cls, inspect.isclass) if issubclass(member, IntEnum))
        clean_members = []
        prefix = camel_to_snake(enum.__name__).upper()
        for member_name, member in enum.__members__.items():
            clean = member_name.removeprefix(f"{prefix}_")
            clean_members.append(f"{clean} = {member.value}")

        snippet = FLAT_ENUM_TEMPLATE.format(
            name=name,
            clean_members="\n    ".join(clean_members),
            snake_name=snake_name,
        )
        flat_src_map[name] = snippet.strip()

    # AST-transformer that replaces those ClassDefs
    class EnumFlattener(pyast.NodeTransformer):
        def visit_ClassDef(self, node: pyast.ClassDef):  # noqa: N802
            if node.name in flat_src_map:
                new_node = pyast.parse(flat_src_map[node.name]).body[0]
                return pyast.copy_location(new_node, node)
            return node

    # Apply transformation
    tree = pyast.parse(protocol.code_outpath.read_text())
    new_tree = EnumFlattener().visit(tree)
    pyast.fix_missing_locations(new_tree)

    # Re-write out custom_types.py with the entire transformed module
    full_code = pyast.unparse(new_tree)
    with protocol.code_outpath.open("w") as out:
        out.write(inject_comment(full_code, CUSTOM_TYPE_COMMENT))


def rewrite_test_custom_types(protocol: ProtocolSpecification) -> None:
    """Rewrite custom_types.py import to accomodate aea message wrapping during .proto generation."""
    content = protocol.test_outpath.read_text()
    a = f"packages.{protocol.author}.protocols.{protocol.name} import {protocol.name}_pb2"
    b = f"packages.{protocol.author}.protocols.{protocol.name}.{protocol.name}_pb2 import {protocol.camel_name}Message as {protocol.name}_pb2  # noqa: N813"  # noqa: E501
    protocol.test_outpath.write_text(content.replace(a, b))


def generate_dialogues(protocol: ProtocolSpecification, template):
    """Generate dialogues.py."""
    output = template.render(**protocol.template_context.model_dump())
    dialogues = protocol.outpath / "dialogues.py"
    dialogues.write_text(output)


def generate_tests_init(protocol: ProtocolSpecification) -> None:
    """Generate tests/__init__.py."""
    test_init_file = protocol.outpath / "tests" / "__init__.py"
    test_init_file.write_text(f'"""Test module for the {protocol.name} protocol."""')


def generate_performative_messages(protocol: ProtocolSpecification, template) -> None:
    """Generate performatives for hypothesis strategy generation."""
    output = template.render(**protocol.template_context.model_dump())
    test_dialogues = protocol.outpath / "tests" / "performatives.py"
    test_dialogues.write_text(output)


def generate_test_dialogues(protocol: ProtocolSpecification, template) -> None:
    """Generate tests/test_dialogue.py."""
    output = template.render(**protocol.template_context.model_dump())
    test_dialogues = protocol.outpath / "tests" / f"test_{protocol.name}_dialogues.py"
    test_dialogues.write_text(output)


def generate_test_messages(protocol: ProtocolSpecification, template) -> None:
    """Generate tests/test_messages.py."""
    output = template.render(**protocol.template_context.model_dump())
    test_messages = protocol.outpath / "tests" / f"test_{protocol.name}_messages.py"
    test_messages.write_text(output)


def update_yaml(protocol, dependencies: dict[str, dict[str, str]]) -> None:
    """Update protocol.yaml dependencies."""
    protocol_yaml = protocol.outpath / "protocol.yaml"
    content = yaml.safe_load(protocol_yaml.read_text())
    for package_name, package_info in dependencies.items():
        content["dependencies"][package_name] = package_info
        content["dependencies"][package_name] = package_info
    protocol_yaml.write_text(yaml.dump(content, sort_keys=False))


def run_adev_fmt(protocol) -> None:
    """Run `adev -v fmt`."""
    command = ["adev", "-v", "fmt", "-p", str(protocol.outpath)]
    run_cli_cmd(command)


def run_adev_lint(protocol) -> None:
    """Run `adev -v lint`."""
    command = ["adev", "-v", "lint", "-p", str(protocol.outpath)]
    run_cli_cmd(command)


def run_aea_fingerprint(protocol) -> None:
    """Run `aea fingerprint protocol`."""
    command = ["aea", "fingerprint", "protocol", protocol.metadata.protocol_specification_id]
    run_cli_cmd(command)


def protocol_scaffolder(protocol_specification_path: str, language, logger, verbose: bool = True):  # noqa: ARG001
    """Scaffolding protocol components.

    Args:
    ----
        protocol_specification_path: Path to the protocol specification file.
        language: Target language for the protocol.
        logger: Logger instance for output and debugging.
        verbose: Whether to enable verbose logging.

    """

    jinja_templates = JinjaTemplates.load()

    agent_dir = Path.cwd()

    # 1. Read spec data
    protocol = read_protocol_spec(protocol_specification_path)

    # 2. AEA generate protocol
    run_aea_generate_protocol(protocol.path, language=language, agent_dir=agent_dir)

    # Ensures `protocol.outpath` exists, required for correct import path generation
    # TODO: on error during any part of this process, clean up (remove) `protocol.outpath`  # noqa: FIX002, TD002, TD003
    run_push_local_protocol(protocol, agent_dir)

    # 3. create README.md
    generate_readme(protocol, jinja_templates.README)

    # 4. Generate custom_types.py and test_custom_types.py
    generate_custom_types(protocol)
    post_enum_processing(protocol)

    # 5. rewrite test_custom_types to patch the import
    rewrite_test_custom_types(protocol)

    # 6. Dialogues
    generate_dialogues(protocol, jinja_templates.dialogues)

    # 7. generate __init__.py in tests folder
    generate_tests_init(protocol)

    # 8. generate performatives
    generate_performative_messages(protocol, jinja_templates.performatives)

    # 9. Test dialogues
    generate_test_dialogues(protocol, jinja_templates.test_dialogues)

    # 10. Test messages
    generate_test_messages(protocol, jinja_templates.test_messages)

    # 11. Update YAML
    dependencies = {"pydantic": {}, "hypothesis": {}}
    update_yaml(protocol, dependencies)

    # 12. fmt
    run_adev_fmt(protocol)

    # 13. lint
    run_adev_lint(protocol)

    # 14. Fingerprint
    run_aea_fingerprint(protocol)

    # Hurray's are in order
    logger.info(f"New protocol scaffolded at {protocol.outpath}")
