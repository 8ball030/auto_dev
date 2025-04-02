import textwrap

from proto_schema_parser import ast
from proto_schema_parser.ast import (
    FileElement,
    File,
    Import,
    Package,
    Option,
    Extension,
    Service,
    MessageElement,
    Comment,
    Field,
    Group,
    OneOf,
    ExtensionRange,
    Reserved,
    Message,
    Enum,
    MapField,
    MessageValue,
    EnumElement,
    FieldCardinality,
)

from auto_dev.protocols import adapters
from auto_dev.protocols.adapters import FileAdapter, MessageAdapter
from auto_dev.protocols.primitives import PRIMITIVE_TYPE_MAP


def render_field(field: Field) -> str:
    field_type = PRIMITIVE_TYPE_MAP.get(field.type, field.type)
    match field.cardinality:
        case FieldCardinality.REQUIRED | None:
            return f"{field_type}"
        case FieldCardinality.OPTIONAL:
            return f"{field_type} | None"
        case FieldCardinality.REPEATED:
            return f"list[{field_type}]"
        case _:
            raise TypeError(f"Unexpected cardinality: {field.cardinality}")


def render_attribute(element: MessageElement | MessageAdapter, prefix: str = "") -> str:
    match type(element):
        case ast.Comment:
            return f"# {element.text}"
        case ast.Field:
            return f"{element.name}: {render_field(element)}"
        case ast.OneOf:
            if not all(isinstance(e, Field) for e in element.elements):
                raise NotImplementedError("Only implemented OneOf for Field")
            inner = " | ".join(render_field(e) for e in element.elements)
            return f"{element.name}: {inner}"
        case adapters.MessageAdapter:
            elements = sorted(element.elements, key=lambda e: not isinstance(e, (MessageAdapter, ast.Enum)))
            body = inner = "\n".join(render_attribute(e, prefix + element.name + ".") for e in elements)
            encoder = render_encoder(element, prefix)
            decoder = render_decoder(element, prefix)
            body = f"{inner}\n\n{encoder}\n\n{decoder}"
            indented_body = textwrap.indent(body, "    ")
            return f"\nclass {element.name}(BaseModel):\n{indented_body}\n"
        case ast.Enum:
            members = "\n".join(f"{val.name} = {val.number}" for val in element.elements)
            indented_members = textwrap.indent(members, "    ")
            return f"class {element.name}(IntEnum):\n{indented_members}\n"
        case ast.MapField:
            key_type = PRIMITIVE_TYPE_MAP.get(element.key_type, element.key_type)
            value_type = PRIMITIVE_TYPE_MAP.get(element.value_type, element.value_type)
            return f"{element.name}: dict[{key_type}, {value_type}]"
        case ast.Group | ast.Option | ast.ExtensionRange | ast.Reserved | ast.Extension:
            raise NotImplementedError(f"{element}")
        case _:
            raise TypeError(f"Unexpected message type: {element}")


def render(file: FileAdapter):

    enums = "\n".join(render_attribute(e) for e in file.enums)
    messages = "\n".join(render_attribute(e) for e in file.messages)

    return f"{enums}\n{messages}"


def encode_field(element, message, prefix):
    instance_attr = f"{message.name.lower()}.{element.name}"
    if element.type in PRIMITIVE_TYPE_MAP:
        value = instance_attr
    elif element.type in message.enum_names:
        value = f"{message.name.lower()}.{element.name}"
    elif element.type in message.file.enum_names:
        value = f"{message.name.lower()}.{element.name}"
    elif element.type in message.message_names:
        value = f"{prefix}{message.name}.{element.type}.encode(proto_obj.{element.name}, {instance_attr})"
        return value
    elif element.type in message.file.message_names:
        value = f"{element.type}.encode(proto_obj.{element.name}, {instance_attr})"
        return value
    else:
        raise ValueError(f"Unexpected element: {element}")

    match element.cardinality:
        case FieldCardinality.REPEATED:
            return f"proto_obj.{element.name}.extend({value})"
        case FieldCardinality.OPTIONAL:
            return f"if {instance_attr} is not None:\n    proto_obj.{element.name} = {instance_attr}"
        case _:
            return f"proto_obj.{element.name} = {value}"


def render_encoder(message: MessageAdapter, prefix="") -> str:

    def encode_element(element, prefix) -> str:
        match type(element):
            case ast.Field:
                return encode_field(element, message, prefix)
            case ast.OneOf:
                return "\n".join(
                    f"if isinstance({message.name.lower()}.{element.name}, {PRIMITIVE_TYPE_MAP.get(e.type, e.type)}):\n    proto_obj.{e.name} = {message.name.lower()}.{element.name}"
                    for e in element.elements
                )
            case ast.MapField:
                iter_items = f"for key, value in {message.name.lower()}.{element.name}.items():"
                if element.value_type in PRIMITIVE_TYPE_MAP:
                    return f"{iter_items}\n    proto_obj.{element.name}[key] = value"
                elif element.value_type in message.file.enum_names:
                    return f"{iter_items}\n    proto_obj.{element.name}[key] = {element.value_type}(value)"
                else:
                    return f"{iter_items}\n    {message.qualified_type(element.value_type)}.encode(proto_obj.{element.name}[key], value)"
            case _:
                raise TypeError(f"Unexpected message type: {element}")

    elements = filter(lambda e: not isinstance(e, (MessageAdapter, ast.Enum)), message.elements)
    inner = "\n".join(encode_element(e, prefix) for e in elements)
    indented_inner = textwrap.indent(inner, "    ")
    return f"@staticmethod\ndef encode(proto_obj, {message.name.lower()}: \"{message.name}\") -> None:\n{indented_inner}"


def decode_field(field: ast.Field, message: MessageAdapter, prefix="") -> str:
    instance_field = f"proto_obj.{field.name}"
    if field.type in PRIMITIVE_TYPE_MAP:
        value = instance_field
    elif field.type in message.enum_names:
        value = instance_field
    elif field.type in message.message_names:
        value = f"{field.name} = {message.qualified_type(field.type)}.decode({instance_field})"
    elif field.type in message.file.message_names:
        value = f"{field.name} = {field.type}.decode({instance_field})"
    else:
        value = instance_field

    match field.cardinality:
        case FieldCardinality.REPEATED:
            return f"{field.name} = list({value})"
        case FieldCardinality.OPTIONAL:
            return (f"{field.name} = {value} "
                    f"if {instance_field} is not None and proto_obj.HasField(\"{field.name}\") "
                    f"else None")
        case FieldCardinality.REQUIRED | None:
            return f"{field.name} = {value}"
        case _:
            raise TypeError(f"Unexpected cardinality: {field.cardinality}")


def render_decoder(message: MessageAdapter, prefix="") -> str:

    def decode_element(element, prefix) -> str:
        match type(element):
            case ast.Field:
                return decode_field(element, message, prefix)
            case ast.OneOf:
                return "\n".join(
                    f"if proto_obj.HasField(\"{e.name}\"):\n    {element.name} = proto_obj.{e.name}"
                    for e in element.elements
                )
            case ast.MapField:
                iter_items = f"{element.name} = {{}}\nfor key, value in proto_obj.{element.name}.items():"
                if element.value_type in PRIMITIVE_TYPE_MAP:
                    return f"{element.name} = dict(proto_obj.{element.name})"
                elif element.value_type in message.file.enum_names:
                    return f"{iter_items}\n    {element.name}[key] = {element.value_type}(value)"
                else:
                    return (f"{element.name} = {{ key: {message.qualified_type(element.value_type)}.decode(item) "
                            f"for key, item in proto_obj.{element.name}.items() }}")
            case _:
                raise TypeError(f"Unexpected message element type: {element}")

    def constructor_kwargs(elements) -> str:
        types = (ast.Field, ast.MapField, ast.OneOf)
        return ",\n    ".join(f"{e.name}={e.name}" for e in elements if isinstance(e, types))

    constructor = f"return cls(\n    {constructor_kwargs(message.elements)}\n)"
    elements = filter(lambda e: not isinstance(e, (MessageAdapter, ast.Enum)), message.elements)
    inner = "\n".join(decode_element(e, prefix) for e in elements) + "\n\n" + constructor
    indented_inner = textwrap.indent(inner, "    ")
    return (f"@classmethod\ndef decode(cls, proto_obj) -> \"{message.name}\":\n{indented_inner}")
