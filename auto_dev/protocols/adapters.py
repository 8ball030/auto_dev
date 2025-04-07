"""Module containing adapter classes for proto_schema_parser."""

from __future__ import annotations

import re
from dataclasses import field, dataclass

from proto_schema_parser.ast import (
    Enum,
    File,
    Field,
    Group,
    OneOf,
    Import,
    Option,
    Comment,
    Message,
    Package,
    Service,
    MapField,
    Reserved,
    Extension,
    FileElement,
    ExtensionRange,
    MessageElement,
)


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


@dataclass
class MessageAdapter:
    """MessageAdapter for proto_schema_parser ast.Message."""

    file: FileAdapter | None = field(repr=False)
    parent: FileAdapter | MessageAdapter | None = field(repr=False)
    wrapped: Message = field(repr=False)
    fully_qualified_name: str
    elements: list[MessageElement | MessageAdapter] = field(default_factory=list, repr=False)

    comments: list[Comment] = field(default_factory=list)
    fields: list[Field] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    oneofs: list[OneOf] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    extension_ranges: list[ExtensionRange] = field(default_factory=list)
    reserved: list[Reserved] = field(default_factory=list)
    messages: list[MessageAdapter] = field(default_factory=list)
    enums: list[Enum] = field(default_factory=list)
    extensions: list[Extension] = field(default_factory=list)
    map_fields: list[MapField] = field(default_factory=list)

    def __getattr__(self, name: str):
        """Access wrapped ast.Message instance attributes."""

        return getattr(self.wrapped, name)

    @property
    def enum_names(self) -> set[str]:
        """Enum names referenced in this ast.Message."""

        return {m.name for m in self.enums}

    @property
    def message_names(self) -> set[str]:
        """Message names referenced in this ast.Message."""

        return {m.name for m in self.messages}

    @classmethod
    def from_message(cls, message: Message, parent_prefix="") -> MessageAdapter:
        """Convert a `Message` into `MessageAdapter`, handling recursion."""

        elements = []
        grouped_elements = {camel_to_snake(t.__name__): [] for t in MessageElement.__args__}
        for element in message.elements:
            key = camel_to_snake(element.__class__.__name__)
            if isinstance(element, Message):
                element = cls.from_message(element, parent_prefix=f"{parent_prefix}{message.name}.")
            elements.append(element)
            grouped_elements[key].append(element)

        return cls(
            file=None,
            parent=None,
            wrapped=message,
            fully_qualified_name=f"{parent_prefix}{message.name}",
            elements=elements,
            comments=grouped_elements["comment"],
            fields=grouped_elements["field"],
            groups=grouped_elements["group"],
            oneofs=grouped_elements["one_of"],
            options=grouped_elements["option"],
            extension_ranges=grouped_elements["extension_range"],
            reserved=grouped_elements["reserved"],
            messages=grouped_elements["message"],
            enums=grouped_elements["enum"],
            extensions=grouped_elements["extension"],
            map_fields=grouped_elements["map_field"],
        )


@dataclass
class FileAdapter:
    """FileAdapter for proto_schema_parser ast.File."""

    wrapped: File = field(repr=False)
    file_elements: list[FileElement | MessageAdapter] = field(repr=False)

    syntax: str | None
    imports: list[Import] = field(default_factory=list)
    packages: list[Package] = field(default_factory=list)
    options: list[Option] = field(default_factory=list)
    messages: list[MessageAdapter] = field(default_factory=list)
    enums: list[Enum] = field(default_factory=list)
    extensions: list[Extension] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)

    def __getattr__(self, name: str):
        """Access wrapped ast.File instance attributes."""

        return getattr(self.wrapped, name)

    @property
    def enum_names(self) -> set[str]:
        """Top-level Enum names in ast.File."""

        return {m.name for m in self.enums}

    @property
    def message_names(self) -> set[str]:
        """Top-level Message names in ast.File."""

        return {m.name for m in self.messages}

    @classmethod
    def from_file(cls, file: File) -> FileAdapter:
        """Convert a `File` into `FileAdapter`, handling messages recursively."""

        file_elements = []
        grouped_elements = {camel_to_snake(t.__name__): [] for t in FileElement.__args__}
        for element in file.file_elements:
            key = camel_to_snake(element.__class__.__name__)
            if isinstance(element, Message):
                element = MessageAdapter.from_message(element)
            file_elements.append(element)
            grouped_elements[key].append(element)

        file_adapter = cls(
            wrapped=file,
            file_elements=file_elements,
            syntax=file.syntax,
            imports=grouped_elements["import"],
            packages=grouped_elements["package"],
            options=grouped_elements["option"],
            messages=grouped_elements["message"],
            enums=grouped_elements["enum"],
            extensions=grouped_elements["extension"],
            services=grouped_elements["service"],
            comments=grouped_elements["comment"],
        )

        def set_parent(message: MessageAdapter, parent: FileAdapter | MessageAdapter):
            message.file = file_adapter
            message.parent = parent
            for nested_message in message.messages:
                set_parent(nested_message, message)

        for message in file_adapter.messages:
            set_parent(message, parent=file_adapter)

        return file_adapter
