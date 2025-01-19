"""Contract functions."""

from enum import Enum
from string import Template
from typing import Any
from dataclasses import dataclass

from auto_dev.contracts.utils import SOLIDITY_TO_PYTHON_TYPES
from auto_dev.contracts.contract_templates import READ_FUNCTION_TEMPLATE, WRITE_FUNCTION_TEMPLATE


class FunctionType(Enum):
    """Enum for function types."""

    READ = "read"
    WRITE = "write"


FUNCTION_TO_TEMPLATE_MAPPING = {
    FunctionType.READ: READ_FUNCTION_TEMPLATE,
    FunctionType.WRITE: WRITE_FUNCTION_TEMPLATE,
}


@dataclass
class ContractFunction:
    """A class to scaffold a read function."""

    w3_function: Any
    function_type: FunctionType

    def __str__(self) -> Template:
        """String representation."""
        template = FUNCTION_TO_TEMPLATE_MAPPING[self.function_type]
        return template.format(
            function_name=self.function_name,
            function_arguments_with_types=self.function_arguments_with_types,
            function_arguments=self.function_arguments,
            function_description=self.function_description,
            function_return_values=self.function_return_values,
        )

    @property
    def function_arguments(self):
        """Parse the w3 function arguments into a string.
        expected format: "arg1, arg2, arg3".
        """
        arguments = []
        for argument in self.w3_function.abi["inputs"]:
            arguments.append(argument["name"])
        return ", ".join(arguments)

    @property
    def function_arguments_with_types(self):
        """Parse the w3 function arguments into a string.
        We need to map the types to python types.
        expected format: "
        arg1: type,
        arg2: type,
        arg3: type.
        """
        arguments = []
        for argument in self.w3_function.abi["inputs"]:
            arguments.append(f"{argument['name']}: {SOLIDITY_TO_PYTHON_TYPES[argument['type']]}")

        return ",\n".join(arguments)

    @property
    def function_description(self) -> str:
        """Parse the w3 function description into a string.
        ensure to use the input and return variables
        expected format: "
            arg1: type,
            arg2: type,
            arg3: type
            return1: type,
            return2: type,
            return3: type.
        """
        return (
            f"{self.w3_function.abi['name']}({self.function_arguments_with_types}) -> ({self.function_return_values})"
        )

    @property
    def function_return_values(self):
        """Parse the w3 function return values.
        expected output:
        return {
            return1: type,
            return2: type,
            return3: type
        }.
        """
        return_values = []
        for return_value in self.w3_function.abi["outputs"]:
            return_values.append(f"{return_value['name']}: {return_value['type']}")
        return ",\n".join(return_values)

    @property
    def function_name(self):
        """Return the function name."""
        return self.w3_function.abi["name"]

    @property
    def function_signature(self):
        """Return the function signature."""
        return self.w3_function.abi["signature"]
