import random
from typing import Any


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
            dummy_instance[prop_name] = [
                _generate_property_dummy_data(prop_schema["items"])
                for _ in range(3)  # Generate 3 items for nested arrays
            ]
        else:
            dummy_instance[prop_name] = _generate_property_dummy_data(prop_schema)
    return dummy_instance


def _generate_property_dummy_data(prop_schema: dict[str, Any]) -> Any:
    prop_type = prop_schema.get("type", "string")

    type_generators = {
        "string": lambda: f"dummy_{random.randint(1000, 9999)}",  # noqa: S311
        "integer": lambda: random.randint(1, 100),  # noqa: S311
        "number": lambda: round(random.uniform(1, 100), 2),  # noqa: S311
        "boolean": lambda: random.choice([True, False]),  # noqa: S311
        "array": lambda: _generate_array_dummy_data(prop_schema),
        "object": lambda: _generate_model_dummy_data(prop_schema),
    }

    return type_generators.get(prop_type, lambda: None)()


def _generate_array_dummy_data(prop_schema: dict[str, Any]) -> list[Any]:
    max_items = prop_schema.get("maxItems", 3)
    num_items = random.randint(1, max_items)  # noqa: S311
    return [_generate_model_dummy_data(prop_schema.get("items", {})) for _ in range(num_items)]


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
                generate_single_dummy_data(model_schema["items"])
                for _ in range(num_items_to_generate)
            ]
        else:
            aggregated_data[model_name] = {
                str(i): generate_single_dummy_data(model_schema)
                for i in range(1, num_items + 1)
            }
    return aggregated_data