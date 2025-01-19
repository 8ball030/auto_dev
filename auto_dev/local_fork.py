"""Module to run a docker container with a fork of the mainnet."""

import time
import platform
import subprocess
from dataclasses import dataclass

import requests
from docker import DockerClient
from docker.models.containers import Container


SLEEP_TIME = 1
PULL_TIMEOUT = 60


@dataclass
class DockerFork:
    """Use a docker container to test contract calls."""

    fork_url: str
    fork_block_number: int

    host: str = "http://localhost"
    port: int = 8546
    container: Container | None = None
    run_command: str = "--fork-url '{fork_url}' --fork-block-number {fork_block_number} --host 0.0.0.0 --port {port}"

    def stop(self) -> None:
        """Stop the docker container."""
        # we force the container to stop
        self.container.stop()
        self.container.remove()

    def is_ready(self):
        """Check if the docker container is ready."""
        try:
            res = requests.post(
                f"{self.host}:{self.port}",
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                },
                timeout=1,
            )
        except requests.exceptions.ConnectionError:
            return False
        except requests.exceptions.ReadTimeout:
            return False
        if res.status_code != 200:
            return False
        return int(res.json()["result"], 16) == self.fork_block_number

    def run(self) -> None:
        """Run the docker container in a background process."""
        client = DockerClient.from_env()

        is_amd64 = platform.machine().lower() in {"x86_64", "amd64"}

        try:
            if is_amd64:
                subprocess.run(
                    ["docker", "pull", "--platform", "linux/amd64", "ghcr.io/foundry-rs/foundry:latest"], check=True
                )
            else:
                client.images.pull("ghcr.io/foundry-rs/foundry:latest")
        except Exception as error:
            msg = f"Failed to pull Docker image: {error!s}"
            raise RuntimeError(msg) from error

        cmd = self.run_command.format(fork_url=self.fork_url, fork_block_number=self.fork_block_number, port=self.port)

        run_kwargs = {
            "image": "ghcr.io/foundry-rs/foundry:latest",
            "entrypoint": "/usr/local/bin/anvil",
            "command": cmd,
            "ports": {f"{self.port}/tcp": self.port},
            "environment": {"RUST_BACKTRACE": "1"},
            "detach": True,
        }

        if is_amd64:
            run_kwargs["platform"] = "linux/amd64"

        self.container = client.containers.run(**run_kwargs)

        wait = 0
        while not self.is_ready():
            time.sleep(SLEEP_TIME)
            wait += SLEEP_TIME
            if wait > PULL_TIMEOUT:
                msg = "Docker fork did not start in time."
                raise TimeoutError(msg)
