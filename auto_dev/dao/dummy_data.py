"""Generate dummy data for the given models."""

import re
from typing import Any


TYPE_TO_GENERATORS = {
    "string": lambda: "STRING_VALUE",
    "integer": lambda: 42,
    "number": lambda: 42.0,
    "boolean": lambda: True,
    "address": lambda: "0x" + "0" * 40,
}


def generate_dummy_data(models: dict[str, Any], num_instances: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Generate dummy data for the given models."""
    dummy_data = {}
    for model_name, model_schema in models.items():
        dummy_data[model_name] = [_generate_model_dummy_data(model_schema) for _ in range(num_instances)]
    return dummy_data


def _generate_model_dummy_data(model_schema: dict[str, Any]) -> dict[str, Any]:
    properties = model_schema.get("properties", {})
    dummy_instance = {}
    for prop_name, prop_schema in properties.items():
        if prop_schema.get("type") == "array":
            dummy_instance[prop_name] = [_generate_property_dummy_data(prop_schema["items"]) for _ in range(3)]
        else:
            dummy_instance[prop_name] = _generate_property_dummy_data(prop_schema)
    return dummy_instance


def _generate_property_dummy_data(prop_schema: dict[str, Any]) -> Any:
    prop_type = prop_schema.get("type", "string")

    if prop_type == "array":
        return [_generate_property_dummy_data(prop_schema["items"])]
    elif prop_type == "object":
        return _generate_model_dummy_data(prop_schema)
    else:
        generator = TYPE_TO_GENERATORS.get(prop_type)
        if generator is None:
            msg = f"Unsupported type: {prop_type}"
            raise ValueError(msg)
        return generator()


def _generate_model_dummy_data(model_schema: dict[str, Any]) -> dict[str, Any]:
    """Generates dummy data for an object/model based on its schema."""
    properties = model_schema.get("properties", {})
    dummy_instance = {}
    for prop_name, prop_schema in properties.items():
        if prop_schema.get("type") == "array":
            dummy_instance[prop_name] = _generate_array_dummy_data(prop_schema)
        else:
            dummy_instance[prop_name] = _generate_property_dummy_data(prop_schema)
    return dummy_instance


def _generate_array_dummy_data(prop_schema: dict[str, Any]) -> list[Any]:
    item_schema = prop_schema.get("items", {})
    return [_generate_model_dummy_data(item_schema)]


def generate_single_dummy_data(model_schema: dict[str, Any]) -> dict[str, Any]:
    """Generate a single instance of dummy data for the given model schema."""
    return _generate_model_dummy_data(model_schema)


def generate_aggregated_dummy_data(models: dict[str, Any], num_items: int = 1) -> dict[str, Any]:
    """Generate aggregated dummy data for the given models."""
    aggregated_data = {}
    for model_name, model_schema in models.items():
        if model_schema.get("type") == "array":
            max_items = model_schema.get("maxItems")
            num_items_to_generate = min(num_items, max_items) if max_items is not None else num_items
            aggregated_data[model_name] = [
                generate_single_dummy_data(model_schema["items"]) for _ in range(num_items_to_generate)
            ]
        else:
            aggregated_data[model_name] = {"1": generate_single_dummy_data(model_schema)}
    return aggregated_data


def normalize_property_name(prop_name: str) -> str:
    """Normalize the property name to snake_case."""
    prop_name = prop_name.replace("-", "_")
    return re.sub(r"(?<!^)(?=[A-Z])", "_", prop_name).lower()
