"""Simple command execution class.
It is used to execute commands in a subprocess and return the output.
It is also used to check if a command was successful or not.
It is used by the lint and test functions.

"""

import os
import subprocess
from typing import Union, List, Optional

from .utils import get_logger


logger = get_logger()


class CommandExecutor:
    """A simple command executor."""

    def __init__(self, command: Union[str, List[str]], cwd: Optional[str] = None):
        """Initialize the command executor."""
        self.command = command
        self.cwd = str(cwd) if cwd else "."
        self.stdout = []
        self.stderr = []
        self.return_code = None
        self.exception = None

    def execute(self, stream=False, verbose: bool = True, shell: bool = False, env_vars: Optional[dict] = None) -> bool:
        """Execute the command."""
        if stream:
            return self._execute_stream(verbose, shell, env_vars)
        if verbose:
            logger.debug(f"Executing command:\n\"\"\n{' '.join(self.command)}\n\"\"")
        try:
            result = subprocess.run(
                self.command,
                capture_output=True,
                cwd=self.cwd,
                check=False,
                env=env_vars,
                shell=shell,
            )
            if verbose:
                if len(result.stdout) > 0:
                    logger.info(result.stdout.decode("utf-8"))
                if len(result.stderr) > 0:
                    logger.error(result.stderr.decode("utf-8"))

            self.stdout = result.stdout.decode("utf-8").splitlines()
            self.stderr = result.stderr.decode("utf-8").splitlines()
            self.return_code = result.returncode
            if result.returncode != 0:
                if verbose:
                    logger.error("Command failed with return code: %s", result.returncode)
                return False
            return True
        except Exception as error:  # pylint: disable=broad-except
            logger.exception("Command failed: %s", error)
            self.exception = error
            return False

    def _execute_stream(self, verbose: bool = True, shell: bool = False, env_vars: Optional[dict] = None) -> Optional[bool]:
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
                env=env_vars,
            ) as process:
                for stdout_line in iter(process.stdout.readline, ""):  # type: ignore
                    self.stdout.append(stdout_line.strip())
                    if verbose:
                        logger.info(stdout_line.strip())
                for stderr_line in iter(process.stderr.readline, ""):
                    self.stderr.append(stderr_line.strip())
                    if verbose:
                        logger.error(stderr_line.strip())
                process.stdout.close()  # type: ignore
                self.return_code = process.wait()
                if self.return_code != 0:
                    if verbose:
                        logger.error("Command failed with return code: %s", self.return_code)
                    return False
                return True
        except KeyboardInterrupt:
            logger.info("Command execution interrupted by user.")
            process.terminate()
            return None
        except Exception as error:  # pylint: disable=broad-except
            logger.exception("Command failed: %s", error)
            self.exception = error
            return False

    @property
    def output(self):
        """Return the output."""
        fmt = f"Command: {' '.join(self.command)}\n"
        fmt += f"Return Code: {self.return_code}\n"
        fmt += "Stdout:\n"
        fmt += "\n\t".join(self.stdout)
        fmt += "\nStderr:\n"
        fmt += "\n\t".join(self.stderr)
        return fmt
