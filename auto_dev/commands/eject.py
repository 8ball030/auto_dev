"""Command to eject components and their dependencies."""

import rich_click as click
from rich.progress import track
from aea.configurations.base import PublicId

from auto_dev.base import build_cli
from auto_dev.services.eject.index import EjectConfig, ComponentEjector


cli = build_cli()


@cli.command()
@click.argument(
    "component_type",
    type=str,
)
@click.argument(
    "public_id",
    type=str,
)
@click.argument(
    "fork_id",
    type=str,
)
@click.option(
    "--skip-dependencies/--no-skip-dependencies",
    is_flag=True,
    help="Skip ejecting dependencies (they must already be ejected)",
)
@click.pass_context
def eject(ctx, component_type: str, public_id: str, fork_id: str, skip_dependencies: bool) -> None:
    """Eject a component and its dependencies to a new fork.

    This command allows you to fork an existing component (skill, contract, connection, or protocol)
    to a new author and name while preserving its functionality. It handles dependency management
    and configuration updates automatically.

    Component Types:
        - skill: Agent skills (e.g., price_estimation, nft_trading)
        - contract: Smart contracts (e.g., token_bridge, amm_contract)
        - connection: Network connections (e.g., http_client, websocket)
        - protocol: Communication protocols (e.g., fipa, http)

    Example Usage:

        # Basic ejection of a skill:
        adev eject skill valory/price_estimation myorg/custom_price

        # Eject a contract without its dependencies:
        adev eject contract valory/gnosis_safe myorg/safe --skip-dependencies

        # Eject a connection with all dependencies:
        adev eject connection valory/http_client myorg/custom_http

        # Eject a protocol to a new name under same author:
        adev eject protocol valory/http valory/custom_http

        # Eject a skill with complex dependencies:
        adev eject skill valory/price_estimation_abci myorg/price_abci

    Args:
        component_type: Type of the component (skill, contract, connection, protocol)
        public_id: Public ID of the component to eject (author/name)
        fork_id: New public ID for the ejected component (author/name)
        skip_dependencies: Skip ejecting dependencies (they must already be ejected)
    """
    logger = ctx.obj["LOGGER"]

    try:
        # Parse component IDs
        public_id_obj = PublicId(author=public_id.split("/")[0], name=public_id.split("/")[1], version="latest")
        fork_id_obj = PublicId(author=fork_id.split("/")[0], name=fork_id.split("/")[1], version="latest")

        # Create eject configuration
        config = EjectConfig(
            component_type=component_type,
            public_id=public_id_obj,
            fork_id=fork_id_obj,
            skip_dependencies=skip_dependencies,
        )

        logger.info(f"Ejecting {public_id} to {fork_id}...")
        logger.info("Analyzing dependency tree...")

        # Create ejector and perform ejection
        ejector = ComponentEjector(config)
        ejected_components = ejector.eject()

        if not ejected_components:
            logger.error("Failed to eject any components!")
            return

        # Report results
        logger.info(f"Successfully ejected {len(ejected_components)} components:")
        for component in ejected_components:
            logger.info(f"  - {component}")

    except Exception as e:
        logger.error(f"Failed to eject component: {e}")
        raise click.ClickException(str(e)) from e


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
