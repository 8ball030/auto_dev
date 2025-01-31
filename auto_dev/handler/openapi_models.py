"""OpenAPI Models."""

import enum
from typing import Any, Union

from pydantic import Field, BaseModel, ConfigDict


class Reference(BaseModel):
    """OpenAPI Reference Object."""

    ref: str = Field(alias="$ref")

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )

    def resolve(self, root_doc: Any) -> Any:
        """Resolve the reference."""
        parts = self.ref.split("/")[1:]
        current = root_doc
        for part in parts:
            current = getattr(current, part, None) or current.get(part)
        return current


class DataType(enum.Enum):
    """Data type."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

    def __str__(self):
        """Return the string representation of the data type."""
        return self.value


class Schema(BaseModel):
    """OpenAPI Schema Object."""

    title: str | None = None
    required: list[str] | None = None
    enum: list[Any] | None = None
    type: DataType | None = None
    items: Union[Reference, "Schema"] | None = None
    properties: dict[str, Union[Reference, "Schema"]] | None = None
    description: str | None = None
    example: Any | None = None
    x_persistent: bool | None = Field(default=None, alias="x-persistent")

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Example(BaseModel):
    """OpenAPI Example Object."""

    summary: str | None = None
    description: str | None = None
    value: Any | None = None


class Encoding(BaseModel):
    """OpenAPI Encoding Object."""

    content_type: str | None = None

    model_config = ConfigDict(
        extra="allow",
    )


class MediaType(BaseModel):
    """OpenAPI Media Type Object."""

    media_type_schema: Reference | Schema | None = Field(default=None, alias="schema")
    example: Any | None = None
    examples: dict[str, Example | Reference] | None = None
    encoding: dict[str, Encoding] | None = None

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Parameter(BaseModel):
    """OpenAPI Parameter Object."""

    description: str | None = None
    required: bool = False
    param_schema: Reference | Schema | None = Field(default=None, alias="schema")
    example: Any | None = None
    examples: dict[str, Example | Reference] | None = None
    content: dict[str, MediaType] | None = None
    name: str
    param_in: str = Field(alias="in")
    schema_: dict | None = Field(default=None, alias="schema")


class RequestBody(BaseModel):
    """OpenAPI Request Body Object."""

    description: str | None = None
    content: dict[str, MediaType]
    required: bool = False


class Response(BaseModel):
    """OpenAPI Response Object."""

    description: str
    content: dict[str, MediaType] | None = None
    headers: dict[str, Any] | None = None

    model_config = ConfigDict(
        extra="allow",
    )


Responses = dict[str, Response | Reference]


class Operation(BaseModel):
    """OpenAPI Operation Object."""

    tags: list[str] | None = None
    summary: str | None = None
    description: str | None = None
    operation_id: str | None = None
    parameters: list[Parameter | Reference] | None = None
    request_body: RequestBody | Reference | None = None
    responses: Responses


class PathItem(BaseModel):
    """OpenAPI Path Item Object."""

    ref: str | None = Field(default=None, alias="$ref")
    summary: str | None = None
    description: str | None = None
    get: Operation | None = None
    put: Operation | None = None
    post: Operation | None = None
    delete: Operation | None = None
    patch: Operation | None = None
    parameters: list[Parameter | Reference] | None = None

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Components(BaseModel):
    """OpenAPI Components Object."""

    schemas: dict[str, Schema | Reference] | None = None


Paths = dict[str, PathItem]


class OpenAPI(BaseModel):
    """OpenAPI Object."""

    openapi: str
    info: dict[str, Any]
    paths: Paths
    components: Components | None = None


Schema.model_rebuild()
