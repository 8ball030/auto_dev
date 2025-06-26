"""Module for testing protocol generation."""

import os
import tempfile
import functools
import subprocess
from pathlib import Path

import pytest

from auto_dev.protocols import protodantic, performatives
from auto_dev.protocols.scaffolder import read_protocol_spec


@functools.lru_cache
def _get_proto_files() -> dict[str, Path]:
    repo_root = protodantic.get_repo_root()
    path = repo_root / "tests" / "data" / "protocols" / "protobuf"
    assert path.exists()
    return {file.name: file for file in path.glob("*.proto")}


@functools.lru_cache
def _get_capitalization_station_protocols() -> dict[str, Path]:
    repo_root = protodantic.get_repo_root()
    path = repo_root / "tests" / "data" / "protocols" / ".capitalisation_station"
    assert path.exists()
    return {file.name: file for file in path.glob("*.yaml")}


PROTO_FILES = _get_proto_files()
PROTOCOL_FILES = _get_capitalization_station_protocols()


@pytest.mark.parametrize(
    "proto_path",
    [
        PROTO_FILES["primitives.proto"],
        PROTO_FILES["optional_primitives.proto"],
        PROTO_FILES["repeated_primitives.proto"],
        PROTO_FILES["basic_enum.proto"],
        PROTO_FILES["optional_enum.proto"],
        PROTO_FILES["repeated_enum.proto"],
        PROTO_FILES["nested_enum.proto"],
        PROTO_FILES["empty_message.proto"],
        PROTO_FILES["simple_message.proto"],
        PROTO_FILES["repeated_message.proto"],
        PROTO_FILES["optional_message.proto"],
        PROTO_FILES["message_reference.proto"],
        PROTO_FILES["nested_message.proto"],
        PROTO_FILES["deeply_nested_message.proto"],
        PROTO_FILES["oneof_value.proto"],
        PROTO_FILES["map_primitive_values.proto"],
        PROTO_FILES["map_enum.proto"],
        PROTO_FILES["map_message.proto"],
        PROTO_FILES["map_optional_primitive_values.proto"],
        PROTO_FILES["map_repeated_primitive_values.proto"],
        PROTO_FILES["map_nested.proto"],
        PROTO_FILES["map_of_map.proto"],
        PROTO_FILES["map_scalar_keys.proto"],
    ],
)
def test_protodantic(proto_path: Path):
    """Test protodantic.create."""

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        code_out = tmp_path / "models.py"
        test_out = tmp_path / "test_models.py"
        (tmp_path / "__init__.py").touch()
        protodantic.create(proto_path, code_out, test_out)
        exit_code = pytest.main([tmp_dir, "-vv", "-s", "--tb=long", "-p", "no:warnings"])
        assert exit_code == 0


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        ("pt:int", "conint(ge=Int32.min(), le=Int32.max())"),
        ("pt:float", "confloat(ge=Double.min(), le=Double.max())"),
        ("pt:list[pt:int]", "tuple[conint(ge=Int32.min(), le=Int32.max())]"),
        ("pt:optional[pt:int]", "Optional[conint(ge=Int32.min(), le=Int32.max())]"),
        ("pt:dict[pt:str, pt:int]", "dict[str, conint(ge=Int32.min(), le=Int32.max())]"),
        (
            "pt:list[pt:union[pt:dict[pt:str, pt:int], pt:list[pt:bytes]]]",
            "tuple[dict[str, conint(ge=Int32.min(), le=Int32.max())] | tuple[bytes]]",
        ),
        (
            "pt:optional[pt:dict[pt:union[pt:str, pt:int], pt:list[pt:union[pt:float, pt:bool]]]]",
            "Optional[dict[str | conint(ge=Int32.min(), le=Int32.max()), tuple[confloat(ge=Double.min(), le=Double.max()) | bool]]]",  # noqa: E501
        ),
    ],
)
def test_parse_performative_annotation(annotation: str, expected: str):
    """Test parse_performative_annotation."""
    assert performatives.parse_annotation(annotation) == expected


@pytest.mark.parametrize(
    "protocol_spec",
    [
        PROTOCOL_FILES["balances.yaml"],
        # PROTOCOL_FILES["bridge.yaml"],  # noqa: ERA001
        # PROTOCOL_FILES["cross_chain_arbtrage.yaml"],  # noqa: ERA001
        # PROTOCOL_FILES["default.yaml"], # noqa: ERA001
        PROTOCOL_FILES["liquidity_provision.yaml"],
        PROTOCOL_FILES["markets.yaml"],
        PROTOCOL_FILES["ohlcv.yaml"],
        # PROTOCOL_FILES["order_book.yaml"],  # noqa: ERA001
        PROTOCOL_FILES["orders.yaml"],
        PROTOCOL_FILES["positions.yaml"],
        PROTOCOL_FILES["spot_asset.yaml"],
        PROTOCOL_FILES["tickers.yaml"],
    ],
)
def test_scaffold_protocol(module_scoped_dummy_agent_tim, protocol_spec: Path):
    """Test `adev scaffold protocol` command."""

    assert module_scoped_dummy_agent_tim

    protocol = read_protocol_spec(protocol_spec)
    repo_root = protodantic.get_repo_root()
    packages_dir = repo_root / "packages"
    protocol_outpath = packages_dir / protocol.metadata.author / "protocols" / protocol.metadata.name

    if protocol_outpath.exists():
        msg = f"Protocol already exists in dummy_agent_tim: {protocol_outpath}"
        raise ValueError(msg)

    # Point PYTHONPATH to the temporary project root so generated modules are discoverable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    command = ["adev", "-v", "scaffold", "protocol", str(protocol_spec)]
    result = subprocess.run(command, env=env, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        msg = f"Protocol scaffolding failed: {result.stderr}"
        raise ValueError(msg)

    assert protocol_outpath.exists()

    test_dir = protocol_outpath / "tests"
    command = ["pytest", str(test_dir), "-vv", "-s", "--tb=long", "-p", "no:warnings"]
    result = subprocess.run(
        command,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, f"Failed pytest on generated protocol: {result.stderr}"
