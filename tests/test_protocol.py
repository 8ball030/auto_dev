import tempfile
import functools
from pathlib import Path

import pytest
from jinja2 import Template, Environment, FileSystemLoader

from auto_dev.protocols import protodantic


@functools.lru_cache()
def _get_proto_files() -> dict[str, Path]:
    repo_root = protodantic.get_repo_root()
    path = repo_root / "tests" / "data" / "protocols" / "protobuf"
    assert path.exists()
    proto_files = {file.name: file for file in path.glob("*.proto")}
    return proto_files


PROTO_FILES = _get_proto_files()


@pytest.mark.parametrize("proto_path", [
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
    PROTO_FILES["message_reference.proto"],
    PROTO_FILES["nested_message.proto"],
    PROTO_FILES["deeply_nested_message.proto"],
    PROTO_FILES["oneof_value.proto"],
    PROTO_FILES["map_primitive_values.proto"],
    PROTO_FILES["map_enum.proto"],
    PROTO_FILES["map_message.proto"],
    PROTO_FILES["map_optional_primitive_values.proto"],
    PROTO_FILES["map_repeated_primitive_values.proto"],
])
def test_protodantic(proto_path: Path):

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        code_out = tmp_path / "models.py"
        test_out = tmp_path / "test_models.py"
        (tmp_path / "__init__.py").touch()
        protodantic.create(proto_path, code_out, test_out)
        exit_code = pytest.main([tmp_dir, "-vv", "-s", "--tb=long", "-p", "no:warnings"])
        assert exit_code == 0
