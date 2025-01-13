"""Contract scaffolder."""

import os
import json
import shutil
from dataclasses import dataclass

from auto_dev.utils import isolated_filesystem
from auto_dev.constants import DEFAULT_ENCODING
from auto_dev.cli_executor import CommandExecutor
from auto_dev.contracts.contract import Contract
from auto_dev.contracts.block_explorer import BlockExplorer


@dataclass
class ContractScaffolder:
    """Class to scaffold a contract."""

    block_explorer: BlockExplorer
    author: str = "eightballer"

    def from_abi(self, path, address: str, name: str):
        """Scaffold a contract from a file."""
        with open(path, encoding=DEFAULT_ENCODING) as file:
            abi = json.load(file)
            if isinstance(abi, dict):
                abi = abi["abi"]
        return Contract(abi=abi, name=name, address=address, author=self.author)

    def from_block_explorer(self, address: str, name: str):
        """Scaffold a contract from a block explorer."""
        abi = self.block_explorer.get_abi(address)
        return Contract(abi=abi, name=name, address=address, author=self.author)

    def generate_openaea_contract(self, contract: Contract):
        """Generate the open-aea contract.
        We will use the contract name to generate the class name.
        We need to;
        - use the temporary directory context manager.
        - create an agent
        - cd into the agent directory
        - scaffold the contract using the name.
        - create a new directory for the contract in the original directory.
        - copy the contract to the new directory.
        """
        verbose = False

        if contract.path.exists():
            msg = f"Contract {contract.name} already exists."
            raise ValueError(msg)

        init_cmd = f"aea init --author {self.author} --reset --ipfs --remote".split(" ")
        if not CommandExecutor(init_cmd).execute(verbose=verbose):
            msg = "Failed to initialise agent lib."
            raise ValueError(msg)

        with isolated_filesystem():
            if not (output := CommandExecutor("aea create myagent".split(" "))).execute(verbose=verbose):
                msg = f"Failed to create agent.\n{output}"
                raise ValueError(msg)
            os.chdir("myagent")
            if not CommandExecutor(f"aea scaffold contract {contract.name}".split(" ")).execute(verbose=verbose):
                msg = "Failed to scaffold contract."
                raise ValueError(msg)

            if not contract.path.parent.exists():
                contract.path.parent.mkdir(parents=True)
            shutil.copytree(
                f"contracts/{contract.name}",
                contract.path,
            )
        return contract.path
