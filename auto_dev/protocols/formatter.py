"""Module with formatter for rendering pydantic model code from proto_schema_parser ast.File."""

import textwrap
from typing import NamedTuple

from proto_schema_parser import ast
from proto_schema_parser.ast import (
    Field,
    MessageElement,
    FieldCardinality,
)

from auto_dev.protocols import adapters
from auto_dev.protocols.adapters import FileAdapter, MessageAdapter
from auto_dev.protocols.primitives import PRIMITIVE_TYPE_MAP


# ruff: noqa: D105, E501, PLR0911


class ResolvedType(NamedTuple):
    """Represents a fully resolved type reference with optional AST context."""

    fully_qualified_name: str
    ast_node: MessageAdapter | ast.Enum | None = None

    @property
    def is_enum(self) -> bool:
        """Return True if the resolved type is an enum."""
        return isinstance(self.ast_node, ast.Enum)

    @property
    def is_message(self) -> bool:
        """Return True if the resolved type is a message."""
        return isinstance(self.ast_node, MessageAdapter)

    def __str__(self):
        return self.fully_qualified_name


def resolve_type(adapter: FileAdapter | MessageAdapter, type_name: str) -> ResolvedType:
    """Fully qualified type for a type reference."""

    if (scalar_type := PRIMITIVE_TYPE_MAP.get(type_name)) is not None:
        return ResolvedType(scalar_type)

    node = adapter.enums_by_name.get(type_name) or adapter.messages_by_name.get(type_name)
    match adapter, node:
        case FileAdapter(), None:
            msg = f"Could not resolve {type_name}"
            raise ValueError(msg)
        case FileAdapter(), _:
            return ResolvedType(type_name, node)
        case MessageAdapter(), None:
            return resolve_type(adapter.parent, type_name)
        case MessageAdapter(), _:
            return ResolvedType(f"{adapter.fully_qualified_name}.{type_name}", node)
        case _:
            msg = f"Unexpected adapter type : {adapter}."
            raise TypeError(msg)


def render_field(field: Field, message: MessageAdapter) -> str:
    """Render Field."""

    resolved_type = resolve_type(message, field.type)
    match field.cardinality:
        case FieldCardinality.REQUIRED | None:
            return f"{resolved_type}"
        case FieldCardinality.OPTIONAL:
            return f"Optional[{resolved_type}] = None"
        case FieldCardinality.REPEATED:
            return f"list[{resolved_type}]"
        case _:
            msg = f"Unexpected cardinality: {field.cardinality}"
            raise TypeError(msg)


def render_attribute(element: MessageElement | MessageAdapter, message: MessageAdapter) -> str:
    """Render message elements."""

    match type(element):
        case ast.Comment:
            return f"# {element.text}"
        case ast.Field:
            return f"{element.name}: {render_field(element, message)}"
        case ast.OneOf:
            if not all(isinstance(e, Field) for e in element.elements):
                msg = "Only implemented OneOf for Field"
                raise NotImplementedError(msg)
            inner = " | ".join(render_field(e, message) for e in element.elements)
            return f"{element.name}: {inner}"
        case adapters.MessageAdapter:
            elements = sorted(element.elements, key=lambda e: not isinstance(e, MessageAdapter | ast.Enum))
            body = inner = "\n".join(render_attribute(e, element) for e in elements)
            encoder = render_encoder(element)
            decoder = render_decoder(element)
            body = f"{inner}\n\n{encoder}\n\n{decoder}"
            indented_body = textwrap.indent(body, "    ")
            return f"\nclass {element.name}(BaseModel):\n" f'    """{element.name}"""\n\n' f"{indented_body}\n"
        case ast.Enum:
            members = "\n".join(f"{val.name} = {val.number}" for val in element.elements)
            indented_members = textwrap.indent(members, "    ")
            return f"class {element.name}(IntEnum):\n" f'    """{element.name}"""\n\n' f"{indented_members}\n"
        case ast.MapField:
            key_type = PRIMITIVE_TYPE_MAP.get(element.key_type, element.key_type)
            value_type = resolve_type(message, element.value_type)
            return f"{element.name}: dict[{key_type}, {value_type}]"
        case ast.Group | ast.Option | ast.ExtensionRange | ast.Reserved | ast.Extension:
            msg = f"{element}"
            raise NotImplementedError(msg)
        case _:
            msg = f"Unexpected message type: {element}"
            raise TypeError(msg)


def render(file: FileAdapter):
    """Main function to render a .proto file."""

    enums = "\n".join(render_attribute(e, file) for e in file.enums)
    messages = "\n".join(render_attribute(e, file) for e in file.messages)

    return f"{enums}\n{messages}"


def encode_field(element, message):
    """Render pydantic model field encoding."""

    instance_attr = f"{message.name.lower()}.{element.name}"
    resolved_type = resolve_type(message, element.type)
    if element.type in PRIMITIVE_TYPE_MAP or resolved_type.is_enum:
        value = instance_attr
    else:  # Message
        if element.cardinality == FieldCardinality.REPEATED:
            return f"for item in {instance_attr}:\n" f"    {resolved_type}.encode(proto_obj.{element.name}.add(), item)"
        if element.cardinality == FieldCardinality.OPTIONAL:
            return (
                f"if {instance_attr} is not None:\n"
                f"    temp = proto_obj.{element.name}.__class__()\n"
                f"    {resolved_type}.encode(temp, {instance_attr})\n"
                f"    proto_obj.{element.name}.CopyFrom(temp)"
            )
        return f"{resolved_type}.encode(proto_obj.{element.name}, {instance_attr})"

    match element.cardinality:
        case FieldCardinality.REPEATED:
            iter_items = f"for item in {value}:\n"
            return f"{iter_items}    proto_obj.{element.name}.append(item)"
        case FieldCardinality.OPTIONAL:
            return f"if {instance_attr} is not None:\n    proto_obj.{element.name} = {instance_attr}"
        case _:
            return f"proto_obj.{element.name} = {value}"


def render_encoder(message: MessageAdapter) -> str:
    """Render pydantic model .encode() method."""

    def encode_element(element) -> str:
        match type(element):
            case ast.Comment:
                return f"# {element.text}"
            case ast.Field:
                return encode_field(element, message)
            case ast.OneOf:
                return "\n".join(
                    f"if isinstance({message.name.lower()}.{element.name}, {PRIMITIVE_TYPE_MAP.get(e.type, e.type)}):\n    proto_obj.{e.name} = {message.name.lower()}.{element.name}"
                    for e in element.elements
                )
            case ast.MapField:
                iter_items = f"for key, value in {message.name.lower()}.{element.name}.items():"
                if element.value_type in PRIMITIVE_TYPE_MAP:
                    return f"{iter_items}\n    proto_obj.{element.name}[key] = value"
                if element.value_type in message.file.enums_by_name:
                    return f"{iter_items}\n    proto_obj.{element.name}[key] = {element.value_type}(value)"
                if element.value_type in message.enums_by_name:
                    return (
                        f"{iter_items}\n    proto_obj.{element.name}[key] = {message.name}.{element.value_type}(value)"
                    )
                return f"{iter_items}\n    {resolve_type(message, element.value_type)}.encode(proto_obj.{element.name}[key], value)"
            case _:
                msg = f"Unexpected message type: {element}"
                raise TypeError(msg)

    elements = filter(lambda e: not isinstance(e, MessageAdapter | ast.Enum), message.elements)
    inner = "\n".join(map(encode_element, elements))
    indented_inner = textwrap.indent(inner, "    ")
    return (
        "@staticmethod\n"
        f"def encode(proto_obj, {message.name.lower()}: {message.name}) -> None:\n"
        f'    """Encode {message.name} to protobuf."""\n\n'
        f"{indented_inner}\n"
    )


def decode_field(field: ast.Field, message: MessageAdapter) -> str:
    """Render pydantic model field decoding."""

    instance_field = f"proto_obj.{field.name}"
    resolved_type = resolve_type(message, field.type)
    if field.type in PRIMITIVE_TYPE_MAP or resolved_type.is_enum:
        value = instance_field
    else:
        resolved_type = resolve_type(message, field.type)
        if field.cardinality == FieldCardinality.REPEATED:
            return f"{field.name} = [{resolved_type}.decode(item) for item in {instance_field}]"
        if field.cardinality == FieldCardinality.OPTIONAL:
            return (
                f"{field.name} = {resolved_type}.decode({instance_field}) "
                f'if {instance_field} is not None and proto_obj.HasField("{field.name}") '
                f"else None"
            )
        return f"{field.name} = {resolved_type}.decode({instance_field})"

    match field.cardinality:
        case FieldCardinality.REPEATED:
            return f"{field.name} = list({value})"
        case FieldCardinality.OPTIONAL:
            return (
                f"{field.name} = {value} "
                f'if {instance_field} is not None and proto_obj.HasField("{field.name}") '
                f"else None"
            )
        case FieldCardinality.REQUIRED | None:
            return f"{field.name} = {value}"
        case _:
            msg = f"Unexpected cardinality: {field.cardinality}"
            raise TypeError(msg)


def render_decoder(message: MessageAdapter) -> str:
    """Render pydantic model .decode() method."""

    def decode_element(element) -> str:
        match type(element):
            case ast.Comment:
                return f"# {element.text}"
            case ast.Field:
                return decode_field(element, message)
            case ast.OneOf:
                return "\n".join(
                    f'if proto_obj.HasField("{e.name}"):\n    {element.name} = proto_obj.{e.name}'
                    for e in element.elements
                )
            case ast.MapField:
                iter_items = f"{element.name} = {{}}\nfor key, value in proto_obj.{element.name}.items():"
                if element.value_type in PRIMITIVE_TYPE_MAP:
                    return f"{element.name} = dict(proto_obj.{element.name})"
                if element.value_type in message.file.enums_by_name:
                    return f"{iter_items}\n    {element.name}[key] = {element.value_type}(value)"
                if element.value_type in message.enums_by_name:
                    return f"{iter_items}\n    {element.name}[key] = {message.name}.{element.value_type}(value)"
                return (
                    f"{element.name} = {{ key: {resolve_type(message, element.value_type)}.decode(item) "
                    f"for key, item in proto_obj.{element.name}.items() }}"
                )
            case _:
                msg = f"Unexpected message element type: {element}"
                raise TypeError(msg)

    def constructor_kwargs(elements) -> str:
        types = (ast.Field, ast.MapField, ast.OneOf)
        return ",\n    ".join(f"{e.name}={e.name}" for e in elements if isinstance(e, types))

    constructor = f"return cls(\n    {constructor_kwargs(message.elements)}\n)"
    elements = filter(lambda e: not isinstance(e, MessageAdapter | ast.Enum), message.elements)
    inner = "\n".join(map(decode_element, elements)) + f"\n\n{constructor}"
    indented_inner = textwrap.indent(inner, "    ")
    return (
        "@classmethod\n"
        f"def decode(cls, proto_obj) -> {message.name}:\n"
        f'    """Decode proto_obj to {message.name}."""\n\n'
        f"{indented_inner}\n"
    )
