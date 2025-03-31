from __future__ import annotations

import re
from typing_extensions import TypeAliasType
from dataclasses import dataclass, field

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
    Field as ProtoField,
    Group,
    OneOf,
    ExtensionRange,
    Reserved,
    Message,
    Enum,
    MapField,
    MessageValue,
    EnumElement,
)


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


@dataclass
class MessageAdapter:
    wrapped: Message = field(repr=False)
    fully_qualified_name: str
    comments: list[Comment] = field(default_factory=list)
    fields: list[ProtoField] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    oneofs: list[OneOf] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    extension_ranges: list[ExtensionRange] = field(default_factory=list)
    reserved: list[Reserved] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    enums: list[Enum] = field(default_factory=list)
    extensions: list[Extension] = field(default_factory=list)
    map_fields: list[MapField] = field(default_factory=list)

    def __getattr__(self, name: str):
        return getattr(self.wrapped, name)

    @classmethod
    def from_message(cls, message: Message, parent_prefix="") -> MessageAdapter:
        """Convert a `Message` into `MessageAdapter`, handling recursion."""

        elements = {camel_to_snake(t.__name__): [] for t in MessageElement.__args__}

        for element in message.elements:
            key = camel_to_snake(element.__class__.__name__)
            elements[key].append(element)

        return cls(
            wrapped=message,
            fully_qualified_name=f"{parent_prefix}{message.name}",
            comments=elements["comment"],
            fields=elements["field"],
            groups=elements["group"],
            oneofs=elements["one_of"],
            options=elements["option"],
            extension_ranges=elements["extension_range"],
            reserved=elements["reserved"],
            messages=[cls.from_message(m, parent_prefix=f"{parent_prefix}{message.name}.") for m in elements["message"]],
            enums=elements["enum"],
            extensions=elements["extension"],
            map_fields=elements["map_field"]
        )


@dataclass
class FileAdapter:
    wrapped: File = field(repr=False)
    syntax: str | None
    imports: list[Import] = field(default_factory=list)
    packages: list[Package] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    enums: list[Enum] = field(default_factory=list)
    extensions: list[Extension] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)

    def __getattr__(self, name: str):
        return getattr(self.wrapped, name)

    @classmethod
    def from_file(cls, file: File) -> FileAdapter:
        """Convert a `File` into `FileAdapter`, handling messages recursively."""

        elements = {camel_to_snake(t.__name__): [] for t in FileElement.__args__}

        for element in file.file_elements:
            key = camel_to_snake(element.__class__.__name__)
            elements[key].append(element)

        return cls(
            wrapped=file,
            syntax=file.syntax,
            imports=elements["import"],
            packages=elements["package"],
            options=elements["option"],
            messages=[MessageAdapter.from_message(m) for m in elements["message"]],
            enums=elements["enum"],
            extensions=elements["extension"],
            services=elements["service"],
            comments=elements["comment"]
        )
