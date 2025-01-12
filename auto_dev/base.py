"""Base CLI for auto_dev."""

import os
from dataclasses import dataclass

import rich_click as click
import pkg_resources

from auto_dev.utils import get_logger
from auto_dev.constants import PLUGIN_FOLDER, DEFAULT_ENCODING


click.rich_click.USE_RICH_MARKUP = True


@dataclass
class CLIs:
    """Base CLI class configurable with plugins."""

    plugin_folder: str = PLUGIN_FOLDER

    def list_commands(self):
        """List commands."""
        results = []
        for filename in os.listdir(self.plugin_folder):
            if filename.endswith(".py") and filename != "__init__.py":
                results.append(filename[:-3])
        results.sort()
        return results

    def get_command(self, name):
        """Get the command."""
        name_space = {}
        file_name = os.path.join(self.plugin_folder, name + ".py")
        with open(file_name, encoding=DEFAULT_ENCODING) as file:
            code = compile(file.read(), file_name, "exec")
            eval(code, name_space, name_space)  # pylint: disable=eval-used
        return name_space[name]

    def get_all_commands(
        self,
    ):
        """Iterate over all commands."""
        for name in self.list_commands():
            yield name, self.get_command(name)


def build_cli(plugins=False):
    """Build the CLI."""

    @click.group()
    @click.option("-v", "--verbose", is_flag=True, default=False)
    @click.option(
        "-l",
        "--log-level",
        default="INFO",
        help="Set the logging level",
        type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    )
    @click.option("-n", "--num-processes", default=0, help="Number of processes to use for linting", type=int)
    @click.option("--version", is_flag=True, help="Print the version and exit")
    @click.option("--remote", is_flag=True, help="Use the remote server wherever possible")
    @click.pass_context
    def cli(ctx, log_level=False, verbose=False, num_processes=1, version=False, remote=False) -> None:
        """Cli development tooling."""
        if version:
            version = pkg_resources.get_distribution("autonomy-dev").version
            click.echo(version)
            ctx.exit()
        ctx.obj = {}
        ctx.obj["VERBOSE"] = verbose
        ctx.obj["LOGGER"] = get_logger(log_level=log_level)
        ctx.obj["REMOTE"] = remote
        if num_processes == 0:
            # we use all available cores
            num_processes = os.cpu_count()
        ctx.obj["NUM_PROCESSES"] = num_processes
        # get the version from the package
        version = pkg_resources.get_distribution("autonomy-dev").version

        ctx.obj["LOGGER"].info(f"Starting Auto Dev v{version} ...")
        # we get the version from the package
        if verbose:
            ctx.obj["LOGGER"].info("Verbose mode enabled")
        if num_processes > 1:
            ctx.obj["LOGGER"].debug(f"Using {num_processes} processes for processing")
        if log_level:
            ctx.obj["LOGGER"].debug(f"Setting log level to {log_level}")

    if plugins:
        plugins = CLIs().get_all_commands()
        for name, plugin in plugins:
            cli.add_command(plugin, name=name)
    return cli
