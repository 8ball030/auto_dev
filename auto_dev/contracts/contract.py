"""Module to represent a contract."""

import json
from typing import Optional
from pathlib import Path

import yaml
from web3 import Web3

from auto_dev.enums import FileType
from auto_dev.utils import write_to_file, snake_to_camel
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.contracts.function import Function
from auto_dev.contracts.contract_events import ContractEvent
from auto_dev.contracts.contract_functions import FunctionType, ContractFunction


DEFAULT_NULL_ADDRESS = "0x0000000000000000000000000000000000000000"


class Contract:
    """Class to scaffold a contract."""

    author: str
    name: str
    abi: dict
    address: str
    read_functions: list = []
    write_functions: list = []
    path: Path
    events: list = []

    def parse_functions(self) -> None:
        """Get the functions from the abi."""
        abi_path = self.path / "build" / f"{self.name}.json"
        if not abi_path.exists():
            msg = f"Abi file {abi_path} does not exist."
            raise ValueError(msg)
        with abi_path.open("r", encoding=DEFAULT_ENCODING) as file_pointer:
            abi = json.load(file_pointer)["abi"]
        w3_contract = self.web3.eth.contract(address=self.address, abi=abi)
        for function in w3_contract.all_functions():
            mutability = function.abi["stateMutability"]
            if mutability in {"view", "pure"}:
                self.read_functions.append(Function(function.abi, FunctionType.READ))
            elif mutability in {"nonpayable", "payable"}:
                self.write_functions.append(Function(function.abi, FunctionType.WRITE))
            else:
                msg = f"Function {function} has unknown state mutability: {mutability}"
                raise ValueError(msg)

    def __init__(
        self, author: str, name: str, abi: dict, address: str = DEFAULT_NULL_ADDRESS, web3: Optional[Web3] = None
    ):
        """Initialise the contract."""
        self.author = author
        self.name = name
        self.abi = abi
        self.address = address
        self.path = Path.cwd() / "packages" / self.author / "contracts" / self.name
        self.web3 = web3 if web3 is not None else Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

    def write_abi_to_file(self) -> None:
        """Write the abi to a file."""
        build_path = self.path / "build" / f"{self.name}.json"
        if build_path.exists():
            msg = f"Build file {build_path} already exists."
            raise ValueError(msg)
        build_path.parent.mkdir(parents=False)
        output = {
            "abi": self.abi,
            "_format": "",
            "bytecode": "",
            "sourceName": "",
            "deployedBytecode": "",
            "deployedLinkReferences": "",
        }
        write_to_file(str(build_path), output, FileType.JSON)

    def update_contract_yaml(self) -> None:
        """Perform an update for the contract,yaml to specify the."""
        contract_yaml_path = self.path / "contract.yaml"
        if not contract_yaml_path.exists():
            msg = f"Contract yaml file {contract_yaml_path} does not exist."
            raise ValueError(msg)
        with contract_yaml_path.open("r", encoding=DEFAULT_ENCODING) as file_pointer:
            contract_yaml = yaml.safe_load(file_pointer)
        contract_yaml["contract_interface_paths"]["ethereum"] = f"build/{self.name}.json"
        contract_yaml["class_name"] = snake_to_camel(self.name)
        write_to_file(str(contract_yaml_path), contract_yaml, FileType.YAML)

    def update_contract_py(self) -> None:
        """Update the contract.py file.
        - update the class name.
        - update the contract_id     contract_id = PublicId.from_str("open_aea/scaffold:0.1.0").

        """
        contract_py_path = self.path / "contract.py"
        with contract_py_path.open("r", encoding=DEFAULT_ENCODING) as file_pointer:
            contract_py = file_pointer.read()
        contract_py = contract_py.replace("class MyScaffoldContract", f"class {snake_to_camel(self.name)}")
        contract_py = contract_py.replace(
            'contract_id = PublicId.from_str("open_aea/scaffold:0.1.0")',
            "contract_id = PUBLIC_ID",
        )
        contract_py = contract_py.replace(
            "from aea.configurations.base import PublicId",
            f"from packages.{self.author}.contracts.{self.name} import PUBLIC_ID",
        )

        contract_py = contract_py.replace(
            "from aea.crypto.base import LedgerApi",
            "from aea.crypto.base import LedgerApi, Address",
        )

        read_functions = "\n".join([function.to_string() for function in self.read_functions])
        write_functions = "\n".join([function.to_string() for function in self.write_functions])

        events = "\n".join([event.to_string() for event in self.events])
        contract_str = "\n".join(contract_py.split("/n")[:36]) + read_functions + write_functions + events

        write_to_file(str(contract_py_path), contract_str, FileType.TEXT)

    def update_contract_init__(self) -> None:
        """Append the Public."""
        init_py_path = self.path / "__init__.py"
        public_id = f"PublicId.from_str('{self.author}/{self.name}:0.1.0')"
        content = f"\nfrom aea.configurations.base import PublicId\n\nPUBLIC_ID = {public_id}\n"
        write_to_file(str(init_py_path), content, FileType.TEXT)

    def update_all(self) -> None:
        """Scaffold the contract."""
        self.update_contract_yaml()
        self.update_contract_py()
        self.update_contract_init__()

    def scaffold_read_function(self, function):
        """Scaffold a read function."""
        return ContractFunction(function, FunctionType.READ)

    def process(self) -> None:
        """Scaffold the contract and ensure it is written to the file system."""
        self.write_abi_to_file()
        self.parse_functions()
        self.parse_events()
        self.update_all()

    def parse_events(self):
        """
        We need to parse the events from the abi.
        """
        self.events = [ContractEvent(**event) for event in self.abi if event["type"] == "event"]
