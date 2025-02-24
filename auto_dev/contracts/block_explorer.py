"""Module to interact with the blockchain explorer."""

from dataclasses import dataclass

import requests

from auto_dev.utils import get_logger
from auto_dev.constants import DEFAULT_TIMEOUT, Network
from auto_dev.exceptions import APIError


logger = get_logger()


@dataclass
class BlockExplorer:
    """Class to interact with the blockchain explorer.

    Args:
    ----
        url: The URL of the block explorer API.
        network: The blockchain network to interact with. Must be an instance of Network enum.

    """

    url: str
    network: Network = Network.ETHEREUM

    def __init__(self, url: str, network: Network) -> None:
        self.url = url
        if not isinstance(network, Network):
            msg = "network must be an instance of Network enum"
            raise TypeError(msg)
        self.network = network

    def get_abi(self, address: str) -> dict | None:
        """Get the ABI for the contract at the address.

        Args:
        ----
            address: The contract address to fetch the ABI for

        Returns:
        -------
            Dict containing the ABI if successful, None if failed

        Raises:
        ------
            requests.exceptions.RequestException: If the API request fails
            ValueError: If the response is invalid or missing ABI data

        """
        try:
            url = f"{self.url}/{address}"
            params = {}
            if self.network != Network.ETHEREUM:
                if not isinstance(self.network, Network):
                    msg = f"Invalid network: {self.network}"
                    raise ValueError(msg)
                params["network"] = self.network.value

            response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)

            if not response.ok:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                msg = f"API request failed with status {response.status_code}: {response.text}"
                raise APIError(msg)

            data = response.json()
            if not data.get("ok", False):
                msg = f"API not ok in {self.network} response: {data}"
                raise APIError(msg)

            if "abi" not in data:
                msg = f"No ABI found in {self.network} response: {data}"
                raise ValueError(msg)

            return data["abi"]

        except requests.exceptions.RequestException as e:
            logger.exception(f"Request failed in {self.network}: {e!s}")
            msg = f"Request failed in {self.network}: {e!s}"
            raise APIError(msg) from e
