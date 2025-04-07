"""Simple command execution class.
It is used to execute commands in a subprocess and return the output.
It is also used to check if a command was successful or not.
It is used by the lint and test functions.

"""

import threading
import subprocess

from .utils import get_logger


class CommandExecutor:
    """A simple command executor.

    Args:
    ----
        command: The command to execute, either as a string or list of strings.
        cwd: The working directory to execute the command in. Defaults to current directory.

    """

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

    def __init__(self, command: str | list[str], cwd: str | None = None, logger=None):
        self.command = command
        self.cwd = str(cwd) if cwd else "."
        self.stdout = []
        self.stderr = []
        self.return_code = None
        self.exception = None
        self.logger = logger or get_logger()

    def execute(self, stream=False, verbose: bool = True, shell: bool = False, env_vars: dict | None = None) -> bool:
        """Execute the command."""
        if stream:
            return self._execute_stream(verbose, shell, env_vars)

        if verbose:
            self.logger.debug(f"Executing command:\n\"\"\n{' '.join(self.command)}\n\"\"\n")

        try:
            result = subprocess.run(
                self.command,
                capture_output=True,
                cwd=self.cwd,
                check=False,
                env=env_vars,
                shell=shell,
            )

            # Store output without logging
            self.stdout = result.stdout.decode("utf-8").splitlines()
            self.stderr = result.stderr.decode("utf-8").splitlines()
            self.return_code = result.returncode

            # Only log if there's actual output and verbose is enabled
            if verbose and result.stdout:
                self.logger.info(result.stdout.decode("utf-8"))
            if verbose and result.stderr:
                self.logger.error(result.stderr.decode("utf-8"))
            if verbose and result.returncode != 0:
                self.logger.error("Command failed with return code: %s", result.returncode)

            return result.returncode == 0
        except Exception as error:  # pylint: disable=broad-except
            if verbose:
                self.logger.exception("Command failed: %s", error)
            self.exception = error
            return False

    def _execute_stream(self, verbose: bool = True, shell: bool = False, env_vars: dict | None = None) -> bool | None:
        """Stream the command output. Especially useful for long running commands."""
        if verbose:
            self.logger.debug(f"Executing command:\n\"\"\n{' '.join(self.command)}\n\"\"")

        self.stdout = []
        self.stderr = []

        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                universal_newlines=True,
                shell=shell,
                env=env_vars,
                bufsize=1,  # Line buffering
            )

            # Process output from both streams
            self._handle_process_output(process, verbose)

            # Get return code and log if needed
            self.return_code = process.returncode
            if self.return_code != 0 and verbose:
                self.logger.error("Command failed with return code: %s", self.return_code)

            return self.return_code == 0

        except KeyboardInterrupt:
            if verbose:
                self.logger.info("Command execution interrupted by user.")
            if "process" in locals():
                process.terminate()
            self.exception = KeyboardInterrupt
            return None
        except Exception as error:  # pylint: disable=broad-except
            if verbose:
                self.logger.exception("Command failed: %s", error)
            self.exception = error
            return False

    def _handle_process_output(self, process, verbose):
        """Handle output streams from a subprocess using threads."""

        # Create thread to process stdout
        def process_stdout():
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    stripped_line = line.strip()
                    if stripped_line:
                        self.stdout.append(stripped_line)
                        if verbose:
                            self.logger.info(stripped_line)
                process.stdout.close()

        # Create thread to process stderr
        def process_stderr():
            if process.stderr:
                for line in iter(process.stderr.readline, ""):
                    stripped_line = line.strip()
                    if stripped_line:
                        self.stderr.append(stripped_line)
                        if verbose:
                            self.logger.error(stripped_line)
                process.stderr.close()

        # Start output processing threads
        stdout_thread = threading.Thread(target=process_stdout)
        stderr_thread = threading.Thread(target=process_stderr)

        stdout_thread.daemon = True
        stderr_thread.daemon = True

        stdout_thread.start()
        stderr_thread.start()

        # Wait for process to complete
        process.wait()

        # Wait for output processing to complete
        stdout_thread.join()
        stderr_thread.join()
