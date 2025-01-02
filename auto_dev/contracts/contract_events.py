"""
Class to represent and parse contract events.
"""

from dataclasses import dataclass

from auto_dev.utils import camel_to_snake
from auto_dev.contracts.utils import SOLIDITY_TO_PYTHON_TYPES
from auto_dev.contracts.contract_templates import EVENT_TEMPLATE


@dataclass
class ContractEvent:
    """Data class to represent a solidity event"""

    anonymous: bool
    inputs: list
    name: str
    type: str

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
            params=self.inputs_with_types(),
            args=self.args(),
            camel_name=self.name,
        )
