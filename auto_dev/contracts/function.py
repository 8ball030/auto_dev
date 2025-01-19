"""Function class."""

from typing import Any
from dataclasses import dataclass

from auto_dev.utils import camel_to_snake
from auto_dev.contracts.variable import Variable
from auto_dev.contracts.contract_functions import FUNCTION_TO_TEMPLATE_MAPPING, FunctionType


@dataclass
class Function:
    """A function of a contract."""

    abi: dict[str, Any]
    function_type: FunctionType

    def to_string(self):
        """Returns the function as a string."""
        spacer = ",\n" + (" " * 8)
        returns = spacer.join([param.to_str_return() for param in self.outputs])
        args = spacer.join([param.to_str_arg() for param in self.inputs])
        params = spacer.join([param.to_str_params() for param in self.inputs])
        function_template = FUNCTION_TO_TEMPLATE_MAPPING[self.function_type]
        return function_template.substitute(
            name=self.name if self.name != "" else "constructor",
            camel_name=self.camel_case_name if self.name != "" else "constructor",
            params=params,
            args=args,
            returns=returns,
        )

    @property
    def name(self):
        """Return the name of the function."""
        return camel_to_snake(self.abi["name"])

    @property
    def camel_case_name(self):
        """Return the name of the function."""
        return self.abi["name"]

    @property
    def inputs(self):
        """Return the inputs as variables."""
        return [Variable(**param, index=ix) for ix, param in enumerate(self.abi["inputs"])]

    @property
    def outputs(self):
        """Return the outputs as variables."""
        return [Variable(**param, index=ix) for ix, param in enumerate(self.abi["outputs"])]

    @property
    def is_read_only(self):
        """Is the function read only."""
        return self.abi["stateMutability"] == "view"
