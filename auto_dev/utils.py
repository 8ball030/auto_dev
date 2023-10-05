"""
Utilities for auto_dev.
"""
import json
import logging
import os
import shutil
import subprocess
from contextlib import contextmanager
from functools import reduce
from glob import glob
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from rich.logging import RichHandler

from .constants import AUTONOMY_PACKAGES_FILE, DEFAULT_ENCODING


def get_logger(name=__name__, log_level="INFO"):
    """Get the logger."""
    msg_format = "%(message)s"
    handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
    )
    logging.basicConfig(level="NOTSET", format=msg_format, datefmt="[%X]", handlers=[handler])

    log = logging.getLogger(name)
    log.setLevel(log_level)
    return log


def get_packages():
    """Get the packages file."""
    with open(AUTONOMY_PACKAGES_FILE, "r", encoding=DEFAULT_ENCODING) as file:
        packages = json.load(file)
    dev_packages = packages["dev"]
    results = []
    for package in dev_packages:
        component_type, author, component_name, _ = package.split("/")
        package_path = Path(f"packages/{author}/{component_type}s/{component_name}")
        if not package_path.exists():
            raise FileNotFoundError(f"Package {package} not found at: {package_path} does not exist")
        results.append(package_path)
    return results


def has_package_code_changed(package_path: Path):
    """
    We use git to effectively check if the code has changed.
    We filter out any files that are ;
    - not tracked by git
    - have no changes to the code in;
      - the package itself
      - the tests for the package

    """
    if not package_path.exists():
        raise FileNotFoundError(f"Package {package_path} does not exist")
    command = f"git status --short {package_path}"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    changed_files = [f for f in result.stdout.decode().split("\n") if f != '']
    changed_files = [f.replace(" M ", "") for f in changed_files]
    changed_files = [f.replace("?? ", "") for f in changed_files]
    return changed_files


def get_paths(path: Optional[str] = None, changed_only: bool = False):
    """Get the paths."""
    if not path and not Path(AUTONOMY_PACKAGES_FILE).exists():
        raise FileNotFoundError("No path was provided and no default packages file found")
    packages = get_packages() if not path else [Path(path)]

    if changed_only:
        all_changed_files = []
        for package in packages:
            changed_files = has_package_code_changed(package)
            if changed_files:
                all_changed_files += changed_files
        packages = all_changed_files
    else:
        python_files = [glob(f"{package}/**/*py", recursive=True) for package in packages]
        if not python_files:
            return []
        packages = reduce(lambda x, y: x + y, python_files)
    if not packages:
        return []
    python_files = [f for f in packages if "__pycache__" not in f and f.endswith(".py")]
    return python_files


@contextmanager
def isolated_filesystem(copy_cwd: bool = False):
    """
    Context manager to create an isolated file system.
    And to navigate to it and then to clean it up.
    """
    original_path = Path.cwd()
    with TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        if copy_cwd:
            # we copy the content of the original directory into the temporary one
            for file_name in os.listdir(original_path):
                if file_name == "__pycache__":
                    continue
                file_path = Path(original_path, file_name)
                if file_path.is_file():
                    shutil.copy(file_path, temp_dir)
                elif file_path.is_dir():
                    shutil.copytree(file_path, Path(temp_dir, file_name))
        yield str(Path(temp_dir))
    os.chdir(original_path)


@contextmanager
def change_dir(target_path):
    """
    Temporarily change the working directory.
    """
    original_path = os.getcwd()
    try:
        os.chdir(target_path)
        yield
    finally:
        os.chdir(original_path)
