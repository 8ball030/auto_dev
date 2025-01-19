"""Simple cli to allow users to perform the following actions against an autonomy repo."""

from auto_dev.base import build_cli


cli = build_cli(plugins=True)

if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
