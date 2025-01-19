"""Module to interact with the blockchain explorer."""

import json
from typing import Dict, Optional
from dataclasses import dataclass

import requests
from web3 import Web3

from auto_dev.utils import get_logger
from auto_dev.constants import DEFAULT_TIMEOUT, Network
from auto_dev.exceptions import APIError


logger = get_logger()


@dataclass
class BlockExplorer:
    """Class to interact with the blockchain explorer."""

    url: str
    network: Network = Network.ETHEREUM

    # Note: this is used to pass tests
    def __init__(self, url: str, network: Network) -> None:
        """Initialize the block explorer."""
        self.url = url
        if not isinstance(network, Network):
            raise TypeError("network must be an instance of Network enum")
        self.network = network

    def get_abi(self, address: str) -> Optional[Dict]:
        """
        Get the ABI for the contract at the address.

        Args:
            address: The contract address to fetch the ABI for

        Returns:
            Dict containing the ABI if successful, None if failed

        Raises:
            requests.exceptions.RequestException: If the API request fails
            ValueError: If the response is invalid or missing ABI data
        """
        try:
            url = f"{self.url}/{address}"
            params = {}
            if self.network != Network.ETHEREUM:
                if not isinstance(self.network, Network):
                    raise ValueError(f"Invalid network: {self.network}")
                params["network"] = self.network.value

            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if not response.ok:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                raise APIError(f"API request failed with status {response.status_code}: {response.text}")

            data = response.json()
            if not data.get("ok", False):
                raise APIError(f"API not ok in {self.network} response: {data}")

            if "abi" not in data:
                raise ValueError(f"No ABI found in {self.network} response: {data}")

            return data["abi"]

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed in {self.network}: {str(e)}")
            raise APIError(f"Request failed in {self.network}: {str(e)}") from e
