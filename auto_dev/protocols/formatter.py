"""Module with formatter for rendering pydantic model code from proto_schema_parser ast.File."""

import textwrap

from proto_schema_parser import ast
from proto_schema_parser.ast import (
    Field,
    MessageElement,
    FieldCardinality,
)

from auto_dev.protocols import adapters
from auto_dev.protocols.adapters import FileAdapter, MessageAdapter
from auto_dev.protocols.primitives import PRIMITIVE_TYPE_MAP


# ruff: noqa: E501, PLR0911


def qualified_type(adapter: FileAdapter | MessageAdapter, type_name: str) -> str:
    """Fully qualified type for a type reference."""

    def find_definition(scope):
        if scope is None or isinstance(scope, FileAdapter):
            return None
        if type_name in scope.enum_names or type_name in scope.message_names:
            return f"{scope.fully_qualified_name}.{type_name}"
        return find_definition(scope.parent)

    qualified_name = find_definition(adapter)
    return qualified_name if qualified_name is not None else PRIMITIVE_TYPE_MAP.get(type_name, type_name)


def render_field(field: Field, message: MessageAdapter) -> str:
    """Render Field."""

    field_type = qualified_type(message, field.type)
    match field.cardinality:
        case FieldCardinality.REQUIRED | None:
            return f"{field_type}"
        case FieldCardinality.OPTIONAL:
            return f"{field_type} | None"
        case FieldCardinality.REPEATED:
            return f"list[{field_type}]"
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
            value_type = qualified_type(message, element.value_type)
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
    if (
        element.type in PRIMITIVE_TYPE_MAP
        or element.type in message.enum_names
        or element.type in message.file.enum_names
    ):
        value = instance_attr
    else:  # Message
        qualified = qualified_type(message, element.type)
        if element.cardinality == FieldCardinality.REPEATED:
            return f"for item in {instance_attr}:\n" f"    {qualified}.encode(proto_obj.{element.name}.add(), item)"
        if element.cardinality == FieldCardinality.OPTIONAL:
            return (
                f"if {instance_attr} is not None:\n"
                f"    temp = proto_obj.{element.name}.__class__()\n"
                f"    {qualified}.encode(temp, {instance_attr})\n"
                f"    proto_obj.{element.name}.CopyFrom(temp)"
            )
        return f"{qualified}.encode(proto_obj.{element.name}, {instance_attr})"

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
                if element.value_type in message.file.enum_names:
                    return f"{iter_items}\n    proto_obj.{element.name}[key] = {element.value_type}(value)"
                if element.value_type in message.enum_names:
                    return (
                        f"{iter_items}\n    proto_obj.{element.name}[key] = {message.name}.{element.value_type}(value)"
                    )
                return f"{iter_items}\n    {qualified_type(message, element.value_type)}.encode(proto_obj.{element.name}[key], value)"
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
    if field.type in PRIMITIVE_TYPE_MAP or field.type in message.enum_names or field.type in message.file.enum_names:
        value = instance_field
    else:
        qualified = qualified_type(message, field.type)
        if field.cardinality == FieldCardinality.REPEATED:
            return f"{field.name} = [{qualified}.decode(item) for item in {instance_field}]"
        if field.cardinality == FieldCardinality.OPTIONAL:
            return (
                f"{field.name} = {qualified}.decode({instance_field}) "
                f'if {instance_field} is not None and proto_obj.HasField("{field.name}") '
                f"else None"
            )
        return f"{field.name} = {qualified}.decode({instance_field})"

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
                if element.value_type in message.file.enum_names:
                    return f"{iter_items}\n    {element.name}[key] = {element.value_type}(value)"
                if element.value_type in message.enum_names:
                    return f"{iter_items}\n    {element.name}[key] = {message.name}.{element.value_type}(value)"
                return (
                    f"{element.name} = {{ key: {qualified_type(message, element.value_type)}.decode(item) "
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
