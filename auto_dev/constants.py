"""
Constants for the auto_dev package.
"""

import os
from pathlib import Path

DEFAULT_ENCODING = "utf-8"
DEFAULT_TIMEOUT = 10
# package directory
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PYLAMA_CONFIG = Path(PACKAGE_DIR) / "data" / "pylama.ini"
AUTONOMY_PACKAGES_FILE = "packages/packages.json"
AUTO_DEV_FOLDER = os.path.join(os.path.dirname(__file__))
PLUGIN_FOLDER = os.path.join(AUTO_DEV_FOLDER, "commands")
TEMPLATE_FOLDER = os.path.join(AUTO_DEV_FOLDER, "data", "repo", "templates")
AGENT_TEMPLATE_FOLDER = os.path.join(AUTO_DEV_FOLDER, "data", "agent", "templates")


SAMPLE_PACKAGES_JSON = {
    "packages/packages.json": """
{
    "dev": {
        "agent/eightballer/tmp/aea-config.yaml": "bafybeiaa3jynk3bx4uged6wye7pddkpbyr2t7avzze475vkyu2bbjeddrm"
    },
    "third_party": {
    }
}
"""
}

SAMPLE_PACKAGE_FILE = {
    "packages/eightballer/agents/tmp/aea-config.yaml": """
agent_name: tmp
author: eightballer
version: 0.1.0
license: Apache-2.0
description: ''
aea_version: '>=1.35.0, <2.0.0'
fingerprint: {}
fingerprint_ignore_patterns: []
connections: []
contracts: []
protocols:
- open_aea/signing:1.0.0:bafybeibqlfmikg5hk4phzak6gqzhpkt6akckx7xppbp53mvwt6r73h7tk4
skills: []
default_connection: null
default_ledger: ethereum
required_ledgers:
- ethereum
default_routing: {}
connection_private_key_paths: {}
private_key_paths: {}
logging_config:
  disable_existing_loggers: false
  version: 1
dependencies:
  open-aea-ledger-ethereum: {}
"""
}
