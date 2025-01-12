"""
Class to represent and parse contract events.
"""

from dataclasses import dataclass

from auto_dev.utils import camel_to_snake, snake_to_camel
from auto_dev.contracts.utils import SOLIDITY_TO_PYTHON_TYPES, keyword_to_safe_name
from auto_dev.contracts.variable import Variable
from auto_dev.contracts.contract_templates import EVENT_TEMPLATE


@dataclass
class ContractEvent:
    """Data class to represent a solidity event"""

    anonymous: bool
    inputs: list
    name: str
    type: str

    def vars(self):
        """return variable instances for the inputs."""
        return [Variable(**i) for i in self.inputs]

    def inputs_list(self):
        """Return the inputs as a string."""
        return ", ".join([i["type"] for i in self.inputs])

    def args(self):
        """Return the inputs as a string."""
        return ", ".join([i["name"] for i in self.inputs])

    def inputs_with_types(self):
        """Return the inputs with names."""
        return ", ".join([f"{i['name']}: {SOLIDITY_TO_PYTHON_TYPES[i['type']]} = None" for i in self.inputs])

    def to_string(self):
        """Return the event as a string."""
        return EVENT_TEMPLATE.substitute(
            name=camel_to_snake(self.name),
            params=("=None,".join([var.to_str_params() for var in self.vars()])) + "=None",
            args=",".join([var.to_str_arg() for var in self.vars()]),
            python_names=",".join([var.python_name() for var in self.vars()]),
            keywords=", ".join(v.to_key_value() for v in self.vars()),
            camel_name=self.name,
        )
