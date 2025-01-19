"""Tests for the local fork."""

import sys
import socket

import pytest
import requests

from auto_dev.local_fork import DockerFork


TESTNET_RPC_URL = "https://rpc.ankr.com/eth"
DEFAULT_FORK_BLOCK_NUMBER = 18120809


def get_unused_port():
    """Get an unused port."""
    new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    new_socket.bind(("localhost", 0))
    port = new_socket.getsockname()[1]
    new_socket.close()
    return port


@pytest.fixture
def local_fork():
    """Use a local fork to test contract calls."""

    fork = DockerFork(TESTNET_RPC_URL, DEFAULT_FORK_BLOCK_NUMBER, port=get_unused_port())
    fork.run()
    yield fork
    fork.stop()


@pytest.mark.skipif(sys.platform == "darwin", reason="Test not supported on macOS")
def test_local_fork(local_fork):
    """Test that the local fork is running."""
    assert local_fork.is_ready()


@pytest.mark.skipif(sys.platform == "darwin", reason="Test not supported on macOS")
def test_get_block_number(local_fork):
    """Test that the local fork is running."""
    res = requests.post(
        f"{local_fork.host}:{local_fork.port}",
        json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
        timeout=1,
    )
    assert res.status_code == 200
    assert int(res.json()["result"], 16) == DEFAULT_FORK_BLOCK_NUMBER


@pytest.mark.skipif(sys.platform == "darwin", reason="Test not supported on macOS")
def test_can_run_multiple_forks():
    """Test that we can run multiple forks."""
    fork1 = DockerFork(TESTNET_RPC_URL, DEFAULT_FORK_BLOCK_NUMBER, port=get_unused_port())
    fork1.run()
    fork2 = DockerFork(TESTNET_RPC_URL, DEFAULT_FORK_BLOCK_NUMBER, port=get_unused_port())
    fork2.run()
    assert fork1.is_ready()
    assert fork2.is_ready()
    fork1.stop()
    fork2.stop()
