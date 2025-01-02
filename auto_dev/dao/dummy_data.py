"""Generate dummy data for the given models."""

import re
import random
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable


def generate_ethereum_address() -> str:
    """Generates a fake Ethereum address."""
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))  # noqa: S311


def generate_boolean() -> bool:
    """Generates a random boolean value."""
    return random.choice(["True", "False"])  # noqa: S311


def generate_integer() -> int:
    """Generates a random integer."""
    return random.randint(1, 100)  # noqa: S311


def generate_string() -> str:
    """Generates a random string."""
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz", k=10))  # noqa: S311


def generate_number() -> float:
    """Generates a random float number."""
    return round(random.uniform(1, 100), 2)  # noqa: S311


def generate_chain_id() -> str:
    """Generates a random chain ID."""
    return random.choice(["1", "5", "10", "137", "84532", "42161", "10000"])  # noqa: S311


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


def _generate_property_dummy_data(prop_schema: dict[str, Any], prop_name: str = "") -> Any:
    prop_type = prop_schema.get("type", "string")

    normalized_prop_name = normalize_property_name(prop_name)

    substring_property_generators: dict[str, Callable[[], Any]] = {
        "wallet_address": generate_ethereum_address,
        "token_id": generate_ethereum_address,
        "chain_id": generate_chain_id,
    }

    for substring, generator in substring_property_generators.items():
        if substring in normalized_prop_name:
            return generator()

    type_generators: dict[str, Callable[[], Any]] = {
        "string": generate_string,
        "integer": generate_integer,
        "number": generate_number,
        "boolean": generate_boolean,
        "array": lambda: _generate_array_dummy_data(prop_schema),
        "object": lambda: _generate_model_dummy_data(prop_schema),
    }

    return type_generators.get(prop_type, lambda: None)()


def _generate_model_dummy_data(model_schema: dict[str, Any]) -> dict[str, Any]:
    """Generates dummy data for an object/model based on its schema."""
    properties = model_schema.get("properties", {})
    dummy_instance = {}
    for prop_name, prop_schema in properties.items():
        if prop_schema.get("type") == "array":
            dummy_instance[prop_name] = _generate_array_dummy_data(prop_schema)
        else:
            dummy_instance[prop_name] = _generate_property_dummy_data(prop_schema, prop_name)
    return dummy_instance


def _generate_array_dummy_data(prop_schema: dict[str, Any]) -> list[Any]:
    max_items = prop_schema.get("maxItems", 3)
    num_items = random.randint(1, max_items)  # noqa: S311
    item_schema = prop_schema.get("items", {})
    return [_generate_model_dummy_data(item_schema) for _ in range(num_items)]


def generate_single_dummy_data(model_schema: dict[str, Any]) -> dict[str, Any]:
    """Generate a single instance of dummy data for the given model schema."""
    return _generate_model_dummy_data(model_schema)


def generate_aggregated_dummy_data(models: dict[str, Any], num_items: int = 5) -> dict[str, Any]:
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
            aggregated_data[model_name] = {
                str(i): generate_single_dummy_data(model_schema) for i in range(1, num_items + 1)
            }
    return aggregated_data


def normalize_property_name(prop_name: str) -> str:
    """Normalize the property name to snake_case."""
    prop_name = prop_name.replace("-", "_")
    return re.sub(r"(?<!^)(?=[A-Z])", "_", prop_name).lower()
