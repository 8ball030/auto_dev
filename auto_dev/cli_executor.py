"""
This is a simple command execution class.
It is used to execute commands in a subprocess and return the output.
It is also used to check if a command was successful or not.
It is used by the lint and test functions.

"""

import os
import subprocess
from typing import List, Optional, Union

from .utils import get_logger

logger = get_logger()


class CommandExecutor:
    """A simple command executor."""

    def __init__(self, command: Union[str, List[str]], cwd: Optional[str] = None):
        """Initialize the command executor."""
        self.command = command
        self.cwd = str(cwd) if cwd else '.'

    def execute(self, stream=False, verbose: bool = True, shell: bool = False):
        """Execute the command."""
        if stream:
            return self._execute_stream(verbose, shell)
        logger.debug(f"Executing command:\n\"\"\n{' '.join(self.command)}\n\"\"")
        try:
            result = subprocess.run(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                check=False,
                env=os.environ,
                shell=shell,
            )
            if verbose:
                if len(result.stdout) > 0:
                    logger.info(result.stdout.decode("utf-8"))
                if len(result.stderr) > 0:
                    logger.error(result.stderr.decode("utf-8"))

            if result.returncode != 0:
                if verbose:
                    logger.error("Command failed with return code: %s", result.returncode)
                return False
            return True
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Command failed: %s", error)
            return False

    def _execute_stream(self, verbose: bool = True, shell: bool = False):
        """Stream the command output. Especially useful for long running commands."""
        logger.debug(f"Executing command:\n\"\"\n{' '.join(self.command)}\n\"\"")
        try:
            with subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                universal_newlines=True,
                shell=shell,
            ) as process:
                for stdout_line in iter(process.stdout.readline, ""):  # type: ignore
                    if verbose:
                        logger.info(stdout_line.strip())
                process.stdout.close()  # type: ignore
                return_code = process.wait()
                if return_code != 0:
                    if verbose:
                        logger.error("Command failed with return code: %s", return_code)
                    return False
                return True
        except Exception as error:  # pylint: disable=broad-except
            logger.error("Command failed: %s", error)
            return False
