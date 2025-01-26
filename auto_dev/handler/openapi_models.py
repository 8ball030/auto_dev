"""OpenAPI Models."""

import enum
from typing import Any, Union, Optional

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

    title: Optional[str] = None
    required: Optional[list[str]] = None
    enum: Optional[list[Any]] = None
    type: Optional[DataType] = None
    items: Optional[Union[Reference, "Schema"]] = None
    properties: Optional[dict[str, Union[Reference, "Schema"]]] = None
    description: Optional[str] = None
    example: Optional[Any] = None
    x_persistent: Optional[bool] = Field(default=None, alias="x-persistent")

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Example(BaseModel):
    """OpenAPI Example Object."""

    summary: Optional[str] = None
    description: Optional[str] = None
    value: Optional[Any] = None


class Encoding(BaseModel):
    """OpenAPI Encoding Object."""

    content_type: Optional[str] = None

    model_config = ConfigDict(
        extra="allow",
    )


class MediaType(BaseModel):
    """OpenAPI Media Type Object."""

    media_type_schema: Optional[Union[Reference, Schema]] = Field(default=None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[dict[str, Union[Example, Reference]]] = None
    encoding: Optional[dict[str, Encoding]] = None

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Parameter(BaseModel):
    """OpenAPI Parameter Object."""

    description: Optional[str] = None
    required: bool = False
    param_schema: Optional[Union[Reference, Schema]] = Field(default=None, alias="schema")
    example: Optional[Any] = None
    examples: Optional[dict[str, Union[Example, Reference]]] = None
    content: Optional[dict[str, MediaType]] = None
    name: str
    param_in: str = Field(alias="in")
    schema_: Optional[dict] = Field(default=None, alias="schema")


class RequestBody(BaseModel):
    """OpenAPI Request Body Object."""

    description: Optional[str] = None
    content: dict[str, MediaType]
    required: bool = False


class Response(BaseModel):
    """OpenAPI Response Object."""

    description: str
    content: Optional[dict[str, MediaType]] = None
    headers: Optional[dict[str, Any]] = None

    model_config = ConfigDict(
        extra="allow",
    )


Responses = dict[str, Union[Response, Reference]]


class Operation(BaseModel):
    """OpenAPI Operation Object."""

    tags: Optional[list[str]] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    operation_id: Optional[str] = None
    parameters: Optional[list[Union[Parameter, Reference]]] = None
    request_body: Optional[Union[RequestBody, Reference]] = None
    responses: Responses


class PathItem(BaseModel):
    """OpenAPI Path Item Object."""

    ref: Optional[str] = Field(default=None, alias="$ref")
    summary: Optional[str] = None
    description: Optional[str] = None
    get: Optional[Operation] = None
    put: Optional[Operation] = None
    post: Optional[Operation] = None
    delete: Optional[Operation] = None
    patch: Optional[Operation] = None
    parameters: Optional[list[Union[Parameter, Reference]]] = None

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Components(BaseModel):
    """OpenAPI Components Object."""

    schemas: Optional[dict[str, Union[Schema, Reference]]] = None


Paths = dict[str, PathItem]


class OpenAPI(BaseModel):
    """OpenAPI Object."""

    openapi: str
    info: dict[str, Any]
    paths: Paths
    components: Optional[Components] = None


Schema.model_rebuild()
