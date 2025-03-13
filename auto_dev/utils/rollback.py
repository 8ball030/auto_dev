import os
import signal
import shutil
import tempfile
from pathlib import Path
from contextlib import contextmanager

from auto_dev.utils import signals

# https://www.youtube.com/watch?v=0GRLhpMao3I
# async-signal safe is the strongest concept of reentrancy. 
# async-signal safe implies thread safe.

# signal.SIGKILL cannot be intercepted
SIGNALS_TO_BLOCK = (signal.SIGINT, signal.SIGTERM)


def restore_from_backup(directory: Path, backup: Path):
    for item in directory.rglob("*"):
        backup_item = backup / item.relative_to(directory)
        if item.is_file() or item.is_symlink():
            item.unlink()
        elif item.is_dir() and not backup_item.exists():
            shutil.rmtree(item)

    for item in backup.rglob("*"):
        directory_item = directory / item.relative_to(backup)
        if item.is_symlink():
            directory_item.symlink_to(item.readlink())
        elif item.is_dir():
            directory_item.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            shutil.copy2(item, directory_item)


@contextmanager
def on_exit(directory: Path):
    backup = Path(tempfile.mkdtemp(prefix="backup_")) / directory.name
    shutil.copytree(directory, backup, symlinks=True)
    try:
        yield
    finally:
        with signals.mask(*SIGNALS_TO_BLOCK):
            restore_from_backup(directory, backup)
        shutil.rmtree(backup)


@contextmanager
def on_exception(directory: Path):
    backup = Path(tempfile.mkdtemp(prefix="backup_")) / directory.name
    shutil.copytree(directory, backup, symlinks=True)
    try:
        yield
    except BaseException:
        with signals.mask(*SIGNALS_TO_BLOCK):
            restore_from_backup(directory, backup)
        raise
    finally:
        shutil.rmtree(backup)
