"""OpenAPI Utilities."""

import re
from typing import Any, Dict, List, Union, Optional

from pydantic import ValidationError

from auto_dev.utils import validate_openapi_spec
from auto_dev.exceptions import ScaffolderError
from auto_dev.commands.metadata import read_yaml_file
from auto_dev.handler.openapi_models import Schema, OpenAPI, Operation, Reference


class CrudOperation:
    """Crud operation."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    OTHER = "other"


def load_openapi_spec(file_path: str, logger) -> OpenAPI:
    """Load the OpenAPI specification from a file."""
    try:
        openapi_spec_dict = read_yaml_file(file_path)

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
        msg = f"OpenAPI specification file not found: {file_path}"
        logger.exception(msg)
        raise ScaffolderError(msg) from e


def get_crud_classification(openapi_spec: OpenAPI, logger) -> Optional[List[Dict]]:
    """Get CRUD classification from OpenAPI spec."""
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
            operation: Optional[Operation] = getattr(path_item, method.lower(), None)
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
    logger.debug(f"Classifications: {classifications}")
    return classifications


def classify_post_operation(operation: Operation, path: str, logger) -> str:
    """Classify a POST operation as CRUD or other based on heuristics."""
    crud_type = CrudOperation.OTHER
    keywords = (
        (operation.operation_id or "") + " " + (operation.summary or "") + " " + (operation.description or "")
    ).lower()

    logger.debug(f"Classifying POST operation '{operation.operation_id}' at path '{path}' with keywords '{keywords}'")

    # Check for 201 Created response
    if crud_type == CrudOperation.OTHER and any(code == "201" for code in operation.responses):
        logger.debug("Found 201 response, classifying as CREATE")
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
        logger.debug(log_msg)

    logger.debug(f"Final classification for {path}: {crud_type}")
    return crud_type


def parse_schema_like(data: Union[Dict[str, Any], Reference, Schema]) -> Union[Schema, Reference]:
    """Parse a schema-like object."""
    if isinstance(data, (Schema, Reference)):
        return data
    if isinstance(data, dict):
        if "$ref" in data:
            return Reference(**data)
        return Schema(**data)
    return data
