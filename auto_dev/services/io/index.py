"""Service functions for file input/output operations.

This module provides a standardized way to handle file operations including:
- Loading and saving data in various formats (YAML, JSON)
- Parsing key-value pairs from strings
- Handling file encoding and format validation

The IO service is designed to be used across the application to ensure consistent
file handling and error reporting.
"""

import json
from typing import Any

import yaml


class IO:
    """A service class to handle data serialization and deserialization operations.

    This class provides static methods for common I/O operations including:
    - Loading data from YAML and JSON files
    - Saving data to YAML and JSON files
    - Parsing key-value pairs from strings

    The class is designed to be used as a service, with all methods being static
    to allow for easy access across the application.

    Example usage:
        ```python
        # Load data from a YAML file
        data = IO.load_data("config.yaml")

        # Save data to a JSON file
        IO.dump_data(data, "output.json")

        # Parse key-value pairs
        params = IO.parse_key_value_pairs("key1=value1,key2=value2")
        ```
    """

    @staticmethod
    def load_data(file_path: str) -> dict[str, Any]:
        """Load data from a file, supporting both YAML and JSON formats.

        Args:
        ----
            file_path: Path to the file to load. Must end in .yaml, .yml, or .json

        Returns:
        -------
            dict[str, Any]: The loaded data as a dictionary

        Raises:
        ------
            ValueError: If the file format is not supported
            FileNotFoundError: If the file does not exist
            yaml.YAMLError: If the YAML file is malformed
            json.JSONDecodeError: If the JSON file is malformed

        """
        with open(file_path, encoding="utf-8") as file:
            if file_path.endswith((".yaml", ".yml")):
                return yaml.safe_load(file)
            if file_path.endswith(".json"):
                return json.load(file)
            msg = f"Unsupported file format for {file_path}"
            raise ValueError(msg)

    @staticmethod
    def dump_data(data: dict[str, Any], file_path: str) -> None:
        """Dump data to a file, supporting both YAML and JSON formats.

        Args:
        ----
            data: The data to save, must be JSON-serializable
            file_path: Path where to save the file. Must end in .yaml, .yml, or .json

        Raises:
        ------
            ValueError: If the file format is not supported
            TypeError: If the data is not JSON-serializable
            OSError: If there are file permission issues

        """
        with open(file_path, "w", encoding="utf-8") as file:
            if file_path.endswith((".yaml", ".yml")):
                yaml.safe_dump(data, file, default_flow_style=False)
            elif file_path.endswith(".json"):
                json.dump(data, file, indent=2)
            else:
                msg = f"Unsupported file format for {file_path}"
                raise ValueError(msg)

    @staticmethod
    def parse_key_value_pairs(params_str: str) -> dict[str, str]:
        """Parse key-value pairs from a string format.

        Takes a string in the format 'key1=value1,key2=value2' and converts it
        to a dictionary. Useful for parsing command line arguments or configuration
        strings.

        Args:
        ----
            params_str: String containing key-value pairs separated by commas,
                       where each pair is separated by an equals sign

        Returns:
        -------
            dict[str, str]: Dictionary containing the parsed key-value pairs

        Example:
        -------
            >>> IO.parse_key_value_pairs("name=test,version=1.0")
            {'name': 'test', 'version': '1.0'}

        """
        if not params_str:
            return {}

        pairs = {}
        for pair in params_str.split(","):
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            pairs[key.strip()] = value.strip()
        return pairs
