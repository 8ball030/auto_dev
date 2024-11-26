"""OpenAPI Utilities."""

import re

from pydantic import ValidationError

from auto_dev.utils import validate_openapi_spec
from auto_dev.commands.metadata import read_yaml_file
from auto_dev.handler.exceptions import ScaffolderError
from auto_dev.handler.openapi_models import Schema, OpenAPI, Operation, Reference


class CrudOperation:
    """Crud operation."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


def load_openapi_spec(spec_file_path: str, logger) -> OpenAPI:
    """Load the OpenAPI spec."""
    try:
        openapi_spec_dict = read_yaml_file(spec_file_path)

        if not validate_openapi_spec(openapi_spec_dict, logger):
            msg = "OpenAPI specification failed schema validation"
            raise ScaffolderError(msg)

        try:
            return OpenAPI(**openapi_spec_dict)
        except ValidationError as e:
            msg = f"OpenAPI specification failed type validation: {e}"
            logger.exception(msg)
            raise ScaffolderError(msg) from e

    except FileNotFoundError as e:
        msg = f"OpenAPI specification file not found: {spec_file_path}"
        logger.exception(msg)
        raise ScaffolderError(msg) from e


def get_crud_classification(openapi_spec: OpenAPI, logger) -> list[dict]:
    """Get the CRUD classification."""
    classifications = []
    for path, path_item in openapi_spec.paths.items():
        if isinstance(path_item, Reference):
            try:
                path_item = path_item.resolve(openapi_spec)
            except Exception as e:
                msg = f"Failed to resolve reference for path {path}: {e}"
                logger.exception(msg)
                continue

        for method in ["get", "post", "put", "delete", "patch", "options", "head", "trace"]:
            operation: Operation | None = getattr(path_item, method.lower(), None)
            if operation:
                if method in {"patch", "options", "head", "trace"}:
                    msg = f"Method {method.upper()} is not currently supported"
                    raise ScaffolderError(msg)

                crud_type = classify_post_operation(operation, path, logger) if method == "post" else "read"
                classifications.append(
                    {
                        "path": path,
                        "method": method,
                        "operationId": operation.operation_id,
                        "crud_type": crud_type,
                    }
                )
    logger.info(f"Classifications: {classifications}")
    return classifications


def classify_post_operation(operation: Operation, path: str, logger) -> str:
    """Classify a POST operation as CRUD or other based on heuristics."""
    crud_type = CrudOperation.OTHER
    keywords = (
        (operation.operation_id or "") + " " + (operation.summary or "") + " " + (operation.description or "")
    ).lower()

    # Check for 201 Created response
    if crud_type == CrudOperation.OTHER and any(code == "201" for code in operation.responses):
        crud_type = CrudOperation.CREATE

    # Keyword-based classification
    elif crud_type == CrudOperation.OTHER:
        keyword_map = {
            CrudOperation.CREATE: {"create", "new", "add", "post"},
            CrudOperation.READ: {"read", "get", "fetch", "retrieve", "list"},
            CrudOperation.UPDATE: {"update", "modify", "change", "edit", "patch"},
            CrudOperation.DELETE: {"delete", "remove", "del"},
        }

        for op_type, op_keywords in keyword_map.items():
            if any(word in keywords for word in op_keywords):
                crud_type = op_type
                break

    # Path parameter and response code heuristics
    if crud_type == CrudOperation.OTHER and bool(re.search(r"/\{[^}]+\}", path)):
        success_responses = {code: resp for code, resp in operation.responses.items() if code in {"200", "201", "204"}}
        if "204" in success_responses:
            crud_type = CrudOperation.DELETE
        elif "200" in success_responses:
            crud_type = CrudOperation.UPDATE

    # Log classification
    log_msg = f"Classifying POST operation '{operation.operation_id}' at path '{path}' as {crud_type}."
    if crud_type == CrudOperation.OTHER:
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

    return crud_type


def parse_schema_like(data: dict | Reference | Schema) -> Schema | Reference:
    """Parse a schema-like object into a Schema or Reference."""
    if isinstance(data, Schema | Reference):
        return data
    if isinstance(data, dict):
        if "$ref" in data:
            return Reference(**data)
        return Schema(**data)
    return data