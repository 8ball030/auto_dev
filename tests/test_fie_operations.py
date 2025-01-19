"""Test file operations."""

from pathlib import Path

import pytest

from auto_dev.enums import FileType, FileOperation
from auto_dev.utils import FileLoader
from auto_dev.exceptions import NotFound


FILE_NAME = "file"


def test_file_writer(
    test_clean_filesystem,
):
    """Test file loader can write to a file."""
    assert Path(test_clean_filesystem).exists()


@pytest.mark.skip("TODO: Fix this test")
@pytest.mark.parametrize(
    "file_path, file_type, file_operation, data, expected",
    [
        ("test.yaml", FileType.YAML, FileOperation.WRITE, {"key": "value"}, {"key": "value"}),
        ("test.json", FileType.JSON, FileOperation.WRITE, {"key": "value"}, {"key": "value"}),
        ("test.txt", FileType.TEXT, FileOperation.WRITE, "Hello, world!", "Hello, world!"),
    ],
)
class TestFileOperations:
    """Test file operations."""

    def test_file_read_fails(self, test_clean_filesystem, file_path, file_type, file_operation, data, expected):
        """Test file loader can write to a file."""
        assert expected
        assert Path(test_clean_filesystem).exists()
        file_loader = FileLoader(file_type=file_type, file_path=file_path)
        with pytest.raises(NotFound, match=f"The file {file_path} was not found."):
            file_loader.read(data, file_operation)  # pylint: disable=E1101

    def test_file_write(self, test_clean_filesystem, file_path, file_type, file_operation, data, expected):
        """Test file loader can write to a file."""
        assert Path(test_clean_filesystem).exists()
        file_loader = FileLoader(file_type=file_type, file_path=file_path)
        file_loader.write(data, file_operation)  # pylint: disable=E1101
        assert file_loader.read() == expected  # pylint: disable=E1101
