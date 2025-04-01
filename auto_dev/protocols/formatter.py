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

from auto_dev.protocols.adapters import MessageAdapter
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


def render_attribute(element: MessageElement, prefix=""):
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
        case ast.Message:
            elements = sorted(element.elements, key=lambda e: not isinstance(e, ast.Message))
            inner = "\n".join(render_attribute(e, prefix + element.name + ".") for e in elements)
            indented_inner = textwrap.indent(inner, "    ")
            return f"\nclass {element.name}(BaseModel):\n{indented_inner}\n"
        case ast.Enum:
            members = "\n".join(f"{val.name} = {val.number}" for val in element.elements)
            indented_members = textwrap.indent(members, "    ")
            return f"class {prefix}{element.name}(Enum):\n{indented_members}\n"
        case ast.MapField:
            key_type = PRIMITIVE_TYPE_MAP.get(element.key_type, element.key_type)
            value_type = PRIMITIVE_TYPE_MAP.get(element.value_type, element.value_type)
            return f"{element.name}: dict[{key_type}, {value_type}]"
        case ast.Group | ast.Option | ast.ExtensionRange | ast.Reserved | ast.Extension:
            raise NotImplementedError(f"{element}")
        case _:
            raise TypeError(f"Unexpected message type: {element}")
