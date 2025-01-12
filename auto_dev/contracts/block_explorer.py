"""Module to interact with the blockchain explorer."""

import json
from typing import Dict, Optional
from dataclasses import dataclass

import requests
from web3 import Web3

from auto_dev.constants import DEFAULT_TIMEOUT


@dataclass
class BlockExplorer:
    """Class to interact with the blockchain explorer."""

    url: str
    network: str = "ethereum"

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
            url = f"{self.url}/{address}?network={self.network}"
            response = requests.get(url, timeout=DEFAULT_TIMEOUT)

            if not response.ok:
                print(f"API request failed with status {response.status_code}: {response.text}")
                return None

            data = response.json()
            if not data.get("ok"):
                print(f"API returned error response: {data}")
                return None

            if "abi" not in data:
                print(f"No ABI found in response: {data}")
                return None

            return data["abi"]

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            return None
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse response: {str(e)}")
            return None
