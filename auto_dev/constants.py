"""Constants for the auto_dev package."""

import os
from enum import Enum
from pathlib import Path

from aea.cli.utils.config import get_or_create_cli_config
from aea.configurations.data_types import PublicId


DEFAULT_ENCODING = "utf-8"
DEFAULT_TZ = "UTC"
DEFAULT_TIMEOUT = 10
DEFAULT_AUTHOR = "author"
DEFAULT_AGENT_NAME = "agent"
DEFAULT_PUBLIC_ID = PublicId.from_str(f"{DEFAULT_AUTHOR}/{DEFAULT_AGENT_NAME}")
FSM_END_CLASS_NAME = "FsmBehaviour"
# package directory
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RUFF_CONFIG = Path(PACKAGE_DIR) / "data" / "ruff.toml"
AUTONOMY_PACKAGES_FILE = "packages/packages.json"
AUTO_DEV_FOLDER = os.path.join(os.path.dirname(__file__))
PLUGIN_FOLDER = os.path.join(AUTO_DEV_FOLDER, "commands")
TEMPLATE_FOLDER = os.path.join(AUTO_DEV_FOLDER, "data", "repo", "templates")
JINJA_TEMPLATE_FOLDER = os.path.join(
    AUTO_DEV_FOLDER,
    "data",
    "templates",
)
WORKFLOWS_FOLDER = os.path.join(
    AUTO_DEV_FOLDER,
    "data",
    "workflows",
)

DOCKERCOMPOSE_TEMPLATE_FOLDER = os.path.join(
    AUTO_DEV_FOLDER,
    "data",
    "templates",
    "compose",
)

AEA_CONFIG = get_or_create_cli_config()
NAME_PATTERN = r"[a-z_][a-z0-9_]{0,127}"

DEFAULT_IPFS_HASH = "bafybeidohldv57m3jkc33zpgbxukaushmcibmt4ncnsnomd3pvpocxs3ui"

SAMPLE_PYTHON_CLI_FILE = """
\"\"\"CLI for {project_name}.\"\"\"

import click

from {project_name}.main import main


@click.command()
def cli():
    \"\"\"CLI entrypoint for the {project_name} module.\"\"\"
    main()
"""


SAMPLE_PYTHON_MAIN_FILE = """
\"\"\"Main module for {project_name}.\"\"\"

def main():
    \"\"\"Main entrypoint for the {project_name} module.\"\"\"
    print("Hello World")

"""

BASE_FSM_SKILLS = {
    "registration_abci": "bafybeib6fsfur5jnflcveidnaeylneybwazewufzwa5twnwovdqgwtwsxm",
    "reset_pause_abci": "bafybeibqz7y3i4aepuprhijwdydkcsbqjtpeea6gdzpp5fgc6abrvjz25a",
    "termination_abci": "bafybeieb3gnvjxxsh73g67m7rivzknwb63xu4qeagpkv7f4mqz33ecikem",
}
AGENT_PUBLISHED_SUCCESS_MSG = "Agent published successfully."


class CheckResult(Enum):
    """Check result enum."""

    PASS = "PASS"
    FAIL = "FAIL"
    MODIFIED = "MODIFIED"
    SKIPPED = "SKIPPED"


class SupportedOS(Enum):
    """Supported operating systems."""

    LINUX = "Linux"
    DARWIN = "Darwin"


OS_ENV_MAP = {
    SupportedOS.LINUX.value: {
        "NETWORK_MODE": "host",
        "HOST_NAME": "localhost:26658",
    },
    SupportedOS.DARWIN.value: {
        "NETWORK_MODE": "bridge",
        "HOST_NAME": "host.docker.internal:26658",
    },
}


class Network(Enum):
    """Supported blockchain networks."""

    ETHEREUM = "ethereum"
    GOERLI = "goerli"
    SEPOLIA = "sepolia"
    AVALANCHE = "avalanche"
    AVALANCHE_FUJI = "avalancheFuji"
    ARBITRUM = "arbitrum"
    ARBITRUM_GOERLI = "arbitrumGoerli"
    ARBITRUM_NOVA = "arbitrumNova"
    BASE = "base"
    BASE_GOERLI = "baseGoerli"
    BSC = "bsc"
    BSC_TESTNET = "bscTestnet"
    FANTOM = "fantom"
    FANTOM_TESTNET = "fantomTestnet"
    POLYGON = "polygon"
    POLYGON_MUMBAI = "polygonMumbai"
    POLYGON_ZKEVM = "polygonZkEvm"
    POLYGON_ZKEVM_TESTNET = "polygonZkEvmTestnet"
    OPTIMISM = "optimism"
    OPTIMISM_GOERLI = "optimismGoerli"
    GNOSIS = "gnosis"
