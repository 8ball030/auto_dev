"""Protocol scaffolder."""

import re
import ast
import datetime
import tempfile
import textwrap
import subprocess
from typing import Any
from pathlib import Path
from itertools import starmap
from collections import namedtuple

import yaml
from jinja2 import Environment, FileSystemLoader
from aea.protocols.generator.base import ProtocolGenerator

from auto_dev.fmt import Formatter
from auto_dev.utils import currenttz, get_logger, remove_prefix, camel_to_snake, snake_to_camel
from auto_dev.constants import DEFAULT_TZ, DEFAULT_ENCODING, JINJA_TEMPLATE_FOLDER
from auto_dev.data.connections.template import HEADER


ProtocolSpecification = namedtuple("ProtocolSpecification", ["metadata", "custom_types", "speech_acts"])


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
            msg = "Expecting a single code block"
            raise ValueError(msg)
        content = remove_prefix(content.split("```")[1], "yaml")

    # use ProtocolGenerator to validate the specification

    with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as temp_file:
        Path(temp_file.name).write_text(content, encoding=DEFAULT_ENCODING)
        ProtocolGenerator(temp_file.name)

    metadata, custom_types, speech_acts = yaml.safe_load_all(content)

    return ProtocolSpecification(metadata, custom_types, speech_acts)


def get_dummy_data(field):
    """Get dummy data."""
    # We assume this is a custom type MIGHT MAKE A PROBLEM LATER!
    res = 0
    if field["type"] == "str":
        res = f'{field["name"]}'
    if field["type"] == "float":
        res = float(res)
    if field["type"] == "bool":
        res = False
    if field["type"].startswith("List"):
        res = []
    if field["type"].startswith("Dict"):
        res = {}
    if field["type"].startswith("Optional"):
        # We recursively call this function to get the dummy data
        res = get_dummy_data({"type": field["type"].split("Optional[")[1].split("]")[0], "name": field["name"]})
    return res


def parse_enums(protocol: ProtocolSpecification) -> dict[str, dict[str, str]]:
    """Parse enums."""
    enums = {}
    if protocol.custom_types is None:
        return enums
    for ct_name, definition in protocol.custom_types.items():
        if not definition.startswith("enum "):
            continue
        result = re.search(r"\{([^}]*)\}", definition)
        if not result:
            msg = f"Error parsing enum fields from: {definition}"
            raise ValueError(msg)
        fields = {}
        for enum in filter(None, result.group(1).strip().split(";")):
            name, number = enum.split("=")
            fields[name.strip()] = number.strip()
        enums[ct_name[3:]] = fields
    return enums


def get_docstring_index(node: ast.stmt):
    """Get docstring index."""

    def is_docstring(stmt: ast.stmt):
        return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Str)

    return next((i + 1 for i, stmt in enumerate(node.body) if is_docstring(stmt)), 0)


def get_raise_statement(stmt) -> ast.stmt:
    """Get raise statement."""
    return next(
        statement
        for statement in stmt.body
        if isinstance(statement, ast.Raise)
        and isinstance(statement.exc, ast.Name)
        and statement.exc.id == "NotImplementedError"
    )


class EnumModifier:
    """EnumModifier."""

    def __init__(self, protocol_path: Path, logger):
        """Initialize EnumModifier."""
        self.protocol_path = protocol_path
        self.protocol = read_protocol(protocol_path / "README.md")
        self.logger = logger

    def augment_enums(self) -> None:
        """Agument enums."""
        enums = parse_enums(self.protocol)
        if not enums:
            return

        custom_types_path = self.protocol_path / "custom_types.py"
        content = custom_types_path.read_text()
        root = ast.parse(content)

        new_import = ast.ImportFrom(module="enum", names=[ast.alias(name="Enum", asname=None)], level=0)
        root.body.insert(get_docstring_index(root), new_import)

        for node in root.body:
            if isinstance(node, ast.ClassDef) and node.name in enums:
                self._process_enum(node, enums)

        modified_code = ast.unparse(root)
        updated_content = self._update_content(content, modified_code)
        self._format_and_write_to_file(custom_types_path, updated_content)
        self.logger.info(f"Updated: {custom_types_path}")

    def _update_content(self, content: str, modified_code: str):
        i = content.find(modified_code.split("\n")[0])
        return content[:i] + modified_code

    def _format_and_write_to_file(self, file_path: Path, content: str) -> None:
        file_path.write_text(content)
        Formatter(verbose=False, remote=False).format(file_path)

    def _process_enum(self, node: ast.ClassDef, enums) -> None:
        camel_to_snake(node.name)
        node.bases = [ast.Name(id="Enum", ctx=ast.Load())]

        class_attrs = self._create_class_attributes(enums[node.name], node)
        docstring_index = get_docstring_index(node)
        node.body = node.body[:docstring_index] + class_attrs + node.body[docstring_index:]
        self._update_methods(node)

    def _create_class_attributes(self, enum_values: dict[str, str], node: ast.ClassDef):
        def to_ast_assign(attr_name: str, attr_value: str):
            return ast.Assign(
                targets=[ast.Name(id=attr_name, ctx=ast.Store())],
                value=ast.Constant(value=int(attr_value)),
                lineno=node.lineno,
            )

        return list(starmap(to_ast_assign, enum_values.items()))

    def _update_methods(self, node: ast.ClassDef) -> None:
        to_remove = []
        for i, stmt in enumerate(node.body):
            if isinstance(stmt, ast.FunctionDef):
                if stmt.name in {"__init__", "__eq__"}:
                    to_remove.append(i)
                elif stmt.name == "encode":
                    self._modify_encode_function(stmt, node)
                elif stmt.name == "decode":
                    self._modify_decode_function(stmt, node)

        for i in sorted(to_remove, reverse=True):
            node.body.pop(i)

    def _modify_encode_function(self, stmt: ast.stmt, node: ast.ClassDef) -> None:
        name = camel_to_snake(node.name)
        statement = get_raise_statement(stmt)
        j = stmt.body.index(statement)
        stmt.body[j] = ast.Expr(
            value=ast.Assign(
                targets=[
                    ast.Attribute(
                        value=ast.Name(id=f"{name}_protobuf_object", ctx=ast.Load()), attr=name, ctx=ast.Store()
                    )
                ],
                value=ast.Attribute(value=ast.Name(id=f"{name}_object", ctx=ast.Load()), attr="value", ctx=ast.Load()),
                lineno=statement.lineno,
            )
        )

    def _modify_decode_function(self, stmt: ast.stmt, node: ast.ClassDef) -> None:
        name = camel_to_snake(node.name)
        statement = get_raise_statement(stmt)
        j = stmt.body.index(statement)
        stmt.body[j] = ast.Return(
            value=ast.Call(
                func=ast.Name(id=node.name, ctx=ast.Load()),
                args=[
                    ast.Attribute(
                        value=ast.Name(id=f"{name}_protobuf_object", ctx=ast.Load()), attr=name, ctx=ast.Load()
                    )
                ],
                keywords=[],
            )
        )


class CommentSplitter(ast.NodeVisitor):
    """CommentSplitter for parsing AST."""

    def __init__(self, max_line_length=120):
        self.max_line_length = max_line_length
        self.result = []

    def split_docstring(self, docstring):
        """Split docstring."""
        split_lines = []
        for line in docstring.splitlines():
            if len(line) > self.max_line_length:
                indentation = len(line) - len(line.lstrip())
                wrapped_lines = textwrap.wrap(line, width=self.max_line_length, subsequent_indent=" " * indentation)
                split_lines.extend(wrapped_lines)
            else:
                split_lines.append(line)
        return "\n".join(split_lines)

    def visit_FunctionDef(self, node):  # noqa
        """process the function's docstring"""
        if ast.get_docstring(node):
            original_docstring = ast.get_docstring(node, clean=False)
            split_docstring = self.split_docstring(original_docstring)
            node.body[0].value = ast.Str(s=split_docstring)

        # Continue visiting the rest of the function
        self.generic_visit(node)

    def visit_Module(self, node):  # noqa
        """Process the module-level docstring"""
        if ast.get_docstring(node):
            original_docstring = ast.get_docstring(node, clean=False)
            split_docstring = self.split_docstring(original_docstring)
            node.body[0].value = ast.Str(s=split_docstring)

        # Continue visiting the rest of the module
        self.generic_visit(node)


def split_long_comment_lines(code: str, max_line_length: int = 120) -> str:
    """Split long comment lines given a code string."""
    tree = ast.parse(code)
    splitter = CommentSplitter(max_line_length=max_line_length)
    splitter.visit(tree)
    return ast.unparse(tree)


PROTOBUF_TO_PYTHON = {
    "string": "str",
    "int32": "int",
    "int64": "int",
    "float": "float",
    "bool": "bool",
}


def parse_protobuf_type(protobuf_type, required_type_imports=[]):
    """Parse protobuf type into python type."""
    output = {}

    if protobuf_type.startswith("repeated"):
        repeated_type = protobuf_type.split()[1]
        attr_name = protobuf_type.split()[2]
        output["name"] = attr_name
        if repeated_type in PROTOBUF_TO_PYTHON:
            output["type"] = f"List[{PROTOBUF_TO_PYTHON[repeated_type]}] = []"
        else:
            output["type"] = f"List[{repeated_type}] = []"
        required_type_imports.append("List")
    elif protobuf_type.startswith("map"):
        attr_name = protobuf_type.split()[2]
        key_val_part = protobuf_type.split(">")[0]
        key_type_raw, val_type = key_val_part.split(", ")
        key_type = key_type_raw.split("<")[1]
        output["name"] = attr_name
        output["type"] = f"Dict[{PROTOBUF_TO_PYTHON[key_type]}, {PROTOBUF_TO_PYTHON[val_type]}] = {{}}"
        required_type_imports.append("Dict")
    elif protobuf_type.startswith("optional"):
        attr_name = protobuf_type.split()[2]

        output["name"] = attr_name
        output["type"] = f"Optional[{PROTOBUF_TO_PYTHON[protobuf_type.split()[1]]}] = None"
        required_type_imports.append("Optional")
    else:
        _type = protobuf_type.split()[0]
        try:
            attr_name = protobuf_type.split()[1]
        except IndexError as err:
            raise ValueError(f"Error parsing attribute name from: {protobuf_type}") from err

        output["name"] = attr_name
        if _type in PROTOBUF_TO_PYTHON:
            output["type"] = PROTOBUF_TO_PYTHON[_type]
        else:
            output["type"] = _type
    return output


class ProtocolScaffolder:
    """ProtocolScaffolder."""

    def __init__(self, protocol_specification_path: str, language, logger, verbose: bool = True):
        """Initialize ProtocolScaffolder."""
        self.logger = logger or get_logger()
        self.verbose = verbose
        self.language = language
        self.protocol_specification_path = protocol_specification_path
        self.logger.info(f"Read protocol specification: {protocol_specification_path}")

    def generate(self) -> None:
        """Generate protocol."""
        command = f"aea -s generate protocol {self.protocol_specification_path} --l {self.language}"
        result = subprocess.run(command, shell=True, capture_output=True, check=False)
        if result.returncode != 0:
            msg = f"Protocol scaffolding failed: {result.stderr}"
            raise ValueError(msg)

        protocol = read_protocol(self.protocol_specification_path)
        protocol_author = protocol.metadata["author"]
        protocol_name = protocol.metadata["name"]
        protocol_version = protocol.metadata["version"]

        protocol_path = Path.cwd() / "protocols" / protocol_name

        readme = protocol_path / "README.md"
        protocol_definition = Path(self.protocol_specification_path).read_text(encoding=DEFAULT_ENCODING)
        kwargs = {
            "name": " ".join(map(str.capitalize, protocol_name.split("_"))),
            "protocol_definition": protocol_definition,
        }
        content = README_TEMPLATE.format(**kwargs)
        readme.write_text(content.strip(), encoding=DEFAULT_ENCODING)

        EnumModifier(protocol_path, self.logger).augment_enums()

        self.cleanup_protocol(protocol_path, protocol_author, protocol_definition, protocol_name, protocol)
        if protocol.custom_types is not None:
            self.generate_pydantic_models(protocol_path, protocol_name, protocol)
            self.clean_tests(
                protocol_path,
                protocol,
            )
        self.generate_base_models(protocol_path, protocol_name, protocol)

        # We now update the protocol.yaml dependencies key to include 'pydantic'

        protocol_yaml = protocol_path / "protocol.yaml"
        # We keey the order of the yaml file
        content = yaml.safe_load(
            protocol_yaml.read_text(encoding=DEFAULT_ENCODING),
        )
        content["dependencies"]["pydantic"] = {}
        protocol_yaml.write_text(yaml.dump(content, sort_keys=False), encoding=DEFAULT_ENCODING)

        command = f"aea fingerprint protocol {protocol_author}/{protocol_name}:{protocol_version}"
        result = subprocess.run(command, shell=True, capture_output=True, check=False)
        if result.returncode != 0:
            msg = f"Protocol fingerprinting failed: {result.stderr}"
            raise ValueError(msg)

        protocol_path = Path.cwd() / "protocols" / protocol_name

        self.logger.info(f"New protocol scaffolded at {protocol_path}")

    def cleanup_protocol(self, protocol_path, protocol_author, protocol_definition, protocol_name, protocol) -> None:
        """Cleanup protocol."""
        # We add in some files. that are necessary for the protocol to pass linting...
        test_init = protocol_path / "tests" / "__init__.py"
        test_init.touch()

        # We template in the necessary copywrite information
        test_init.write_text(
            HEADER.format(
                author=protocol_author,
                year=datetime.datetime.now(tz=currenttz()).year,
            ),
            encoding=DEFAULT_ENCODING,
        )
        # We make a protocol_spec.yaml file
        protocol_spec = protocol_path / "protocol_spec.yaml"
        protocol_spec.write_text(protocol_definition, encoding=DEFAULT_ENCODING)

        # We remove from the following lines from the *_pb2.py file
        regexs = [
            "_runtime_version",
        ]
        pb2_file = protocol_path / f"{protocol_name}_pb2.py"
        content = pb2_file.read_text(encoding=DEFAULT_ENCODING)
        new_content = ""
        for line in content.splitlines():
            for regex in regexs:
                if regex in line:
                    break
            else:
                new_content += line + "\n"
        pb2_file.write_text(new_content, encoding=DEFAULT_ENCODING)

        # We split long lines in the protocol_spec.yaml file

        if protocol.custom_types:
            custom_types = protocol_path / "custom_types.py"
            content = custom_types.read_text(encoding=DEFAULT_ENCODING)
            updated_content = split_long_comment_lines(content)
            custom_types.write_text(updated_content, encoding=DEFAULT_ENCODING)

    def generate_base_models(self, protocol_path, protocol_name, protocol):
        """Generate base models."""
        raw_classes, all_dummy_data, enums = self._get_definition_of_custom_types(protocol)
        custom_types = protocol_path / "dialogues.py"
        content = custom_types.read_text(encoding=DEFAULT_ENCODING)
        # We want to add to the imports

        new_imports = [
            "from aea.skills.base import Model",
        ]

        content = content.replace(
            f"class {snake_to_camel(protocol_name.capitalize())}Dialogues(Dialogues, ABC):",
            f"class Base{snake_to_camel(protocol_name.capitalize())}Dialogues(Dialogues, ABC):",
        )

        if len(protocol.speech_acts["roles"]) > 1:
            self.logger.error("We do not fully generate all dilogiues classes only support one role in the protocol.")
        role = list(protocol.speech_acts["roles"].keys())[0]

        content = content.replace(
            "role_from_first_message: Callable[[Message, Address], Dialogue.Role],",
            f"role_from_first_message: Callable[[Message, Address], Dialogue.Role] = _role_from_first_message,",
        )

        content_lines = content.split("\n")
        import_end_line = 0
        for i, line in enumerate(content_lines):
            if line.startswith("from"):
                new_imports.append(line)
            if line.startswith("class"):
                break
            import_end_line = i

        # We also want to replace the base class with the correct one.

        dialogues_class_str = textwrap.dedent(f"""
        def _role_from_first_message(message: Message, sender: Address) -> Dialogue.Role:
            '''Infer the role of the agent from an incoming/outgoing first message'''
            del sender, message
            return {snake_to_camel(protocol_name.capitalize())}Dialogue.Role.{role.upper()}
        """)
        dialogues_class_ast = ast.parse(dialogues_class_str)
        dialogues_class_str = ast.unparse(dialogues_class_ast)

        content_lines = (
            content_lines[:import_end_line]
            + new_imports
            + dialogues_class_str.split("\n")
            + content_lines[import_end_line:]
        )

        # noqa
        base_cls_name = f"Base{snake_to_camel(protocol_name.capitalize())}"

        dialogues_class_str = textwrap.dedent(f"""
        class {snake_to_camel(protocol_name.capitalize())}Dialogues({base_cls_name}Dialogues, Model):
            '''This class defines the dialogues used in {protocol_name.capitalize()}.'''
            def __init__(self, **kwargs):
                '''Initialize dialogues.'''
                Model.__init__(self, keep_terminal_state_dialogues=False, **kwargs)
                Base{snake_to_camel(protocol_name.capitalize())}Dialogues.__init__(self, 
                self_address=str(self.context.skill_id))

        """)
        # noqa

        dialogues_class_ast = ast.parse(dialogues_class_str)
        dialogues_class_str = ast.unparse(dialogues_class_ast)

        updated_content = content_lines + dialogues_class_str.split("\n")
        custom_types.write_text("\n".join(updated_content), encoding=DEFAULT_ENCODING)

        # We also need to update the dialogues tests
        dialogues_tests = protocol_path / "tests" / f"test_{protocol_name}_dialogues.py"
        content = dialogues_tests.read_text(encoding=DEFAULT_ENCODING)
        dialogues_tests.write_text(content, encoding=DEFAULT_ENCODING)

        # We just need to perform a simple updating of the dialogues.

        Formatter(verbose=False, remote=False).format(dialogues_tests)
        Formatter(verbose=False, remote=False).format(custom_types)

    def _get_definition_of_custom_types(self, protocol, required_type_imports=["Any"]):
        """Get the definition of data types."""
        raw_classes = []
        all_dummy_data = {}
        enums = parse_enums(protocol)
        if not protocol.custom_types:
            return raw_classes, all_dummy_data, enums
        for custom_type, definition in protocol.custom_types.items():
            if definition.startswith("enum "):
                continue
            class_data = {
                "name": custom_type.split(":")[1],
                "fields": [
                    parse_protobuf_type(field, required_type_imports) for field in definition.split(";\n") if field
                ],
                "type": "data",
            }
            raw_classes.append(class_data)

            dummy_data = {field["name"]: get_dummy_data(field) for field in class_data["fields"]}

            all_dummy_data[class_data["name"]] = dummy_data
        return raw_classes, all_dummy_data, enums

    def generate_pydantic_models(self, protocol_path, protocol_name, protocol):
        """Generate data classes."""
        # We check if there are any custom types
        # We assume the enums are handled correctly,
        # and we only need to generate the data classes
        env = Environment(loader=FileSystemLoader(Path(JINJA_TEMPLATE_FOLDER) / "protocols"), autoescape=True)

        required_type_imports = ["Any"]

        raw_classes, all_dummy_data, enums = self._get_definition_of_custom_types(protocol, required_type_imports)

        # We need to generate the data class
        template = env.get_template("data_class.jinja")
        pydantic_output = template.render(
            classes=raw_classes,
            enums=enums.keys(),
            protocol_name=protocol_name,
        )

        # We write this to a yaml file in the protocol folder
        dummy_data_path = protocol_path / "tests" / "dummy_data.yaml"
        dummy_data_path.write_text(yaml.dump(all_dummy_data), encoding=DEFAULT_ENCODING)

        self.output_pydantic_models(
            pydantic_output,
            protocol_path,
            required_type_imports,
        )

    def output_pydantic_models(
        self,
        pydantic_output,
        protocol_path,
        required_type_imports,
    ):
        """
        Ouput the pydantic models to the custom_types.py file.
        """
        new_ast = ast.parse(pydantic_output)
        new_imports = {}
        new_classes = {}
        new_assignments = {}

        for node in new_ast.body:
            if isinstance(node, ast.Import):
                new_imports[node.names[0].name] = node
                continue
            if isinstance(node, ast.Assign):
                new_assignments[node.targets[0].id] = node
                continue
            if isinstance(node, ast.ClassDef):
                new_classes[node.name] = node
                continue
            raise ValueError(f"Unknown node type: {node}")

        # We now read in the custom_types.py file
        custom_types_path = protocol_path / "custom_types.py"
        content = custom_types_path.read_text()
        root = ast.parse(content)

        # We now update the classes

        classes = {}
        assignments = {}
        imports = {}

        for node in root.body:
            if isinstance(node, ast.ImportFrom):
                imports[node.names[0].name] = node
                continue
            if isinstance(node, ast.ClassDef):
                classes[node.name] = node
                continue
            if isinstance(node, ast.Assign):
                assignments[node.targets[0].id] = node
                continue
            if isinstance(node, ast.Expr):
                continue

        # We now create a set of new  data, such that the new data is added to the custom_types.py file

        new_body = (
            [i for i in imports.values() if i.names[0].name not in new_imports]
            + list(new_imports.values())
            + [i for i in classes.values() if i.name not in new_classes]
            + list(new_classes.values())
            + [i for i in assignments.values() if i.targets[0].id not in new_assignments]
            + list(new_assignments.values())
        )

        root.body = new_body

        # We now write the updated content to the custom_types.py file
        updated_content = ast.unparse(root)
        # We add in the imports
        typing_import_line = textwrap.dedent(
            """
        '''Custom types for the protocol.'''
        from enum import Enum
        from pydantic import BaseModel
        """
        )

        if required_type_imports:
            typing_import_line += f"\nfrom typing import {', '.join(set(required_type_imports))}"

        updated_content_lines = updated_content.split("\n")
        updated_content_lines.insert(0, typing_import_line)

        updated_content = "\n".join(updated_content_lines)
        custom_types_path.write_text(updated_content)
        Formatter(verbose=False, remote=False).format(custom_types_path)

    def clean_tests(
        self,
        protocol_path,
        protocol,
    ) -> None:
        """Clean tests."""
        self.clean_tests_messages(protocol_path, protocol)
        self.clean_tests_dialogues(protocol_path, protocol)

    def clean_tests_messages(
        self,
        protocol_path,
        protocol,
    ) -> None:
        """Clean tests."""
        # We need to remove the test files
        tests_path = protocol_path / "tests" / f"test_{protocol_path.name}_messages.py"

        # We ensure that all enum instances are instantiated with 0 in this file.
        content = tests_path.read_text()

        test_data_loader = textwrap.dedent(
            """
            import os
            import yaml
            def load_data(custom_type):
                '''Load test data.'''
                with open(f"{os.path.dirname(__file__)}/dummy_data.yaml", "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)[custom_type]
            
            """
        )

        for custom_type in protocol.custom_types:
            if protocol.custom_types[custom_type].startswith("enum"):
                ct_name = custom_type.split(":")[1]
                content = content.replace(f"{ct_name}()", f"{ct_name}(0)")
                continue
            # We build the line to load the data types;
            ct_name = custom_type[3:]
            replace_line = f"{ct_name}(**load_data('{ct_name}'))"
            search_line = f"{ct_name}()"
            content = content.replace(search_line, replace_line)

        # We need to insert this at the top of the file just above the first class definition
        original_content = content.split("\n")
        new_content = []
        start_line = 0
        for ix, line in enumerate(original_content):
            if line.startswith("class"):
                break
            start_line = ix

        import_defs = textwrap.dedent(
            """
            from typing import Any
            """
        )
        function_defs = test_data_loader.split("\n")
        new_content.extend(original_content[:start_line])
        new_content.extend([import_defs])
        new_content.extend(function_defs)
        new_content.extend(original_content[start_line:])

        # We drop everyuthing from the start of the line begining `build_inconsistent(self)` to the end of the file

        content = "\n".join(new_content)

        drop_from = content.find("    def build_inconsistent(self)")

        content = content[:drop_from]
        # We then add a single function to the class
        content += textwrap.dedent(
            """
            ----def build_inconsistent(self):
            ----    '''Build inconsistent message.'''
            ----    return []
            """
        )

        content = content.replace("----", "    ")

        # We also make a dummy init file in the tests folder
        tests_init = protocol_path / "tests" / "__init__.py"
        tests_init.touch()
        tests_init.write_text(
            HEADER.format(
                author=protocol.metadata["author"],
                year=datetime.datetime.now(tz=currenttz()).year,
            ),
            encoding=DEFAULT_ENCODING,
        )

        tests_path.write_text(content, encoding=DEFAULT_ENCODING)
        Formatter(verbose=False, remote=False).format(tests_path)

    def clean_tests_dialogues(
        self,
        protocol_path,
        protocol,
    ) -> None:
        """Clean tests."""
        # We need to remove the test files
        tests_path = protocol_path / "tests" / f"test_{protocol_path.name}_dialogues.py"

        content = tests_path.read_text()

        # We just need to find the custom types, and make sure that we use the new data loader function

        enum_imports = []

        for custom_type in protocol.custom_types:
            if protocol.custom_types[custom_type].startswith("enum"):
                ct_name = custom_type.split(":")[1]
                content = content.replace(f"{ct_name}()", f"{ct_name}(0)")
                msg = (
                    f"from packages.{protocol.metadata['author']}"
                    + f".protocols.{protocol_path.name}.custom_types import {ct_name}"
                )
                enum_imports.append(msg)
                continue
            # We build the line to load the data types;
            ct_name = custom_type[3:]
            replace_line = f"{ct_name}(**load_data('{ct_name}'))"
            search_line = f"{ct_name}()"
            content = content.replace(search_line, replace_line)

        # We update the import to import the BaseDialogues class

        for string, replace_line in [
            (
                f"{snake_to_camel(protocol_path.name.capitalize())}Dialogues",
                f"Base{snake_to_camel(protocol_path.name.capitalize())}Dialogues",
            ),
        ]:
            content = content.replace(
                string,
                replace_line,
            )

        # We update the imports
        original_content = content.split("\n")
        new_content = []
        start_line = 0
        for ix, line in enumerate(original_content):
            if line.startswith("class"):
                break
            start_line = ix

        test_data_loader = textwrap.dedent(
            """
            import os
            import yaml
            def load_data(custom_type):
                '''Load test data.'''
                with open(f"{os.path.dirname(__file__)}/dummy_data.yaml", "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)[custom_type]
            
            """
        )

        new_content.extend(original_content[:start_line])
        new_content.extend(enum_imports)
        new_content.extend(test_data_loader.split("\n"))
        new_content.extend(original_content[start_line:])
        content = "\n".join(new_content)

        # We write the updated content to the file
        tests_path.write_text(content, encoding=DEFAULT_ENCODING)

        Formatter(verbose=False, remote=False).format(tests_path)
