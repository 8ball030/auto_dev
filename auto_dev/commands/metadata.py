"""Used to generate metadata for aea packages.
- generate metadata. we read in a meta data file and generate a json file that can be uploaded to ipfs.
- print metadata: we read in a meta data file and print it in a way that can be copy pasted into the frontend.
"""

import sys
import json

import yaml
import rich_click as click
from rich import print_json
from aea.helpers.cid import to_v1
from aea.configurations.base import PublicId
from aea_cli_ipfs.ipfs_utils import IPFSTool
from aea.configurations.constants import (
    AGENT,
    AGENTS,
    CUSTOM,
    SKILLS,
    CUSTOMS,
    SERVICE,
    SERVICES,
    CONTRACTS,
    PROTOCOLS,
    CONNECTIONS,
    DEFAULT_AEA_CONFIG_FILE,
)

from auto_dev.base import build_cli
from auto_dev.enums import FileType
from auto_dev.utils import write_to_file
from auto_dev.constants import DEFAULT_ENCODING


cli = build_cli()


def read_yaml_file(file_path):
    """Reads a yaml file and returns the data."""
    with open(file_path, encoding=DEFAULT_ENCODING) as file:
        return next(iter(yaml.safe_load_all(file)))


def read_json_file(file_path):
    """Reads a json file and returns the data."""
    with open(file_path, encoding=DEFAULT_ENCODING) as file:
        return json.load(file)


def get_metadata(root, name, hash_, target_id):
    """Get metadata for a package by reading in the package.yaml file and then getting
    packages from the yaml keys in the orders of:
    - contracts
    - protocols
    - connections
    - skills
    - agents
    - customs.

    """
    split_name = name.split("/")
    package_type, author, package_name, version = split_name

    file_name = split_name[0] if split_name[0] != "agent" else "aea-config"
    file_name = split_name[0] if split_name[0] != "agent" else "aea-config"

    if package_type == AGENT:
        file_name = DEFAULT_AEA_CONFIG_FILE.split(".", maxsplit=1)[0]
    elif package_type == CUSTOM:
        file_name = "component"
    else:
        file_name = f"{package_type}"

    data = read_yaml_file(root + f"/packages/{author}/{package_type}s/{package_name}/{file_name}.yaml")
    name_ = f"{package_type}/{author}/{package_name}:{version}"
    response = IPFSTool().client.add(
        root + f"/mints/{target_id}.png", pin=True, recursive=True, wrap_with_directory=False
    )
    image_hash = to_v1(response["Hash"])
    return {
        "name": name_,
        "description": data["description"],
        "code_uri": f"ipfs://{hash_}",
        "image": f"ipfs://{image_hash}",
        "attributes": [{"trait_type": "version", "value": f"{split_name[3]}"}],
    }


# we make a command group called metadata


@cli.group()
def metadata() -> None:
    """Commands for generating and printing metadata."""


# we make a command called generate
# we take in the root folder, the target name and the target id.
# we read in the packages.json file and get the hash for the target name.
@cli.command()
@click.argument(
    "root",
    type=click.Path(exists=True),
    default=".",
)
@click.argument(
    "target_name",
    type=str,
)
@click.argument(
    "target_id",
    type=str,
)
@click.option(
    "strict",
    "--strict",
    is_flag=True,
    default=False,
)
@click.option(
    "all",
    "--all",
    is_flag=True,
    default=False,
)
def generate(root, target_name, target_id, strict, all) -> None:  # pylint: disable=redefined-builtin
    """Generate metadata for a package.

    example usage:
         python ./metadata.py generate . contract/eightballer/cool_skill/0.1.0 01

    """
    if not target_id and not all:
        click.echo("Please provide a target id or use --all to generate all metadata.")
        sys.exit(1)
    data = read_json_file(root + "/packages/packages.json")
    id_to_metadata = {}
    for name, hash_ in data["dev"].items():
        if name != target_name and not all:
            continue
        metadata = get_metadata(root, name, hash_, target_id)
        id_to_metadata[target_id] = metadata

    if not id_to_metadata:
        click.echo("No packages found in packages.json")
        sys.exit(1)
    for target_metadata in id_to_metadata.values():
        target_metadata = id_to_metadata.get(target_id)
        if not target_metadata:
            click.echo(f"Package {target_name} not found in packages.json Do you have the correct name?")
            if strict:
                sys.exit(1)
        if strict and not render_metadata(target_metadata):
            click.echo("Metadata generation failed. Please fix the errors above and try again.")
            sys.exit(1)
        write_to_file(root + f"/mints/{target_id}.json", metadata, FileType.JSON)
        click.echo(f"Metadata generated successfully! Saved to: {root}/mints/{target_id}.json")


# we will be minting compoenents sequentially as some components depend on others.
# the order of the dependency is:
# -protocols
# -contracts
# -connections
# -skills
# -agents
# -services
# when we render the metadata we will need to get the dependencies and PRINT them to the user.
# we also need to 2 checks A) if the package is already minted, this will be confirmed by checking
# in the mapping.txt file in the mints folder.
# B) if the package is already minted, we need to check if the hash is the same as the one in the mapping.txt file.
# this will be done later.

dependency_order = [
    PROTOCOLS,
    CONTRACTS,
    CONNECTIONS,
    CUSTOMS,
    SKILLS,
    AGENTS,
    SERVICES,
]


class Dependency(PublicId):
    """Class to represent a dependency."""

    component_type: str


def build_dependency_tree_for_component(component) -> list[str]:
    """Build dependency tree for a component."""
    component_type = component.split("/")[0]
    component_author = component.split("/")[1]
    component_name = component.split("/")[2]
    public_id = PublicId(component_author, component_name.split(":")[0])
    if component_type == AGENT:
        file_name = DEFAULT_AEA_CONFIG_FILE
    elif component_type == SERVICE:
        file_name = "service.yaml"
    elif component_type == CUSTOM:
        file_name = "component.yaml"
    else:
        file_name = f"{component_type}.yaml"

    component_path = f"packages/{public_id.author}/{component_type}s/{public_id.name}/{file_name}"
    component_data = read_yaml_file(component_path)

    dependencies = {}

    for dependency_type in dependency_order:
        if dependency_type == AGENTS and component_type != SERVICE:
            continue
        if component_type == SERVICE and dependency_type == SERVICES:
            dependency_id = Dependency.from_str(component_data[AGENT])
            dependency_id.component_type = AGENT
            path = f"{dependency_type}/{dependency_id.author}/{dependency_id.name}"
            dependencies[dependency_id] = path
        else:
            if dependency_type not in component_data:
                continue
            for dependency in component_data[dependency_type]:
                dependency_id = Dependency.from_str(dependency)
                dependency_id.component_type = dependency_type[:-1]
                path = f"{dependency_type}/{dependency_id.author}/{dependency_id.name}"
                dependencies[dependency_id] = path
    return dependencies


@cli.command()
@click.argument(
    "metadata_file",
    type=click.Path(exists=True),
)
@click.pass_context
def validate(ctx, metadata_file) -> None:
    """Print metadata for a package."""
    verbose = ctx.obj["VERBOSE"]
    metadata = read_json_file(metadata_file)
    valid = render_metadata(metadata, verbose=verbose)
    if not valid:
        click.echo("Metadata validation failed. Please fix the above errors retry.")
        sys.exit(1)


def render_metadata(metadata, verbose=False) -> bool:
    """Render metadata for a package."""
    self_component = Dependency.from_str("/".join(metadata["name"].split("/")[1:]))
    self_component.component_type = metadata["name"].split("/")[0]
    self_component_status, self_component_id = check_component_status(self_component)
    dependencies = build_dependency_tree_for_component(metadata["name"])

    if verbose:
        click.echo("Raw Data:")
        print_json(data=metadata)
        click.echo(
            "\nName:",
        )
        click.echo(metadata["name"])
        click.echo(f"\nType: \n{self_component.component_type}")
        click.echo(
            "\nDescription:",
        )
        click.echo(f"\"{metadata['description']}\"")

        click.echo(
            "\nVersion:",
        )
        click.echo(metadata["attributes"][0]["value"])

        click.echo(
            "\nPackage Hash:",
        )
        click.echo(metadata["code_uri"][14:])
        click.echo(
            "\nNFT Image URL:",
        )
        click.echo(metadata["image"])

        click.echo(
            "\nDependencies:",
        )
    mint_status = {}
    for dependency, path in dependencies.items():
        component_status, component_id = check_component_status(dependency)
        mint_status[component_id] = component_status
        # we use a sexy emjoji to show the status of the minting.
        status_emjoji = "✅" if component_status == "MINTED" else "❌"
        if verbose:
            click.echo(f"Status: {status_emjoji} {component_id or ''} {component_status} - {path}")

    # we print the self mint status
    # we first check that all the dependencies are minted.
    # if they are not minted, we print the dependencies that are not minted.
    # if they are minted, we print the dependecies list.
    # we also print the self mint status.

    for component_id, component_status in mint_status.items():
        if component_status == "NOT MINTED":
            click.echo(f"\n{component_id} is not minted. Please mint it first.")
            return False

    image_hash = metadata["image"][7:]
    click.echo(f"View image at: https://gateway.autonolas.tech/ipfs/{image_hash}")
    click.echo(f"View code at: https://gateway.autonolas.tech/ipfs/{metadata['code_uri'][7:]}")
    click.echo("\nAll dependencies are minted. You can mint this component now.")

    deps_ids_numeric = sorted(map(int, mint_status.keys()))

    if verbose:
        click.echo(f"\nDependencies: \n{list(deps_ids_numeric)}")

        click.echo(
            "\nSelf Mint Status:",
        )
        status_emjoji = "✅" if self_component_status == "MINTED" else "❌"
        click.echo(f"{status_emjoji} {self_component_id or ''} " + f"{self_component_status} - {self_component} ")
    return self_component_status == "MINTED"


def check_component_status(component_id):
    """We check the status of the component by reading the mapping.txt file in the mints folder.
    ➤ cat mints/mapping.txt
    token_id-"component_id"
    # deps
    1-"protocol/valory/abci/0.1.0"
    2-"protocol/valory/acn/1.1.0"
    ...
    51-"contract/valory/multicall2/0.1.0"
    # dev
    97-contract/zarathustra/grow_registry:0.1.0
    ?-skill/zarathustra/plantation_abci/0.1.0.

    NOTES: if the component is NOT present in the mapping.txt file, it is NOT minted.
    if the component is present in the
    we always return the token_id, even if it is not minted.

    """
    with open("mints/mapping.txt", encoding=DEFAULT_ENCODING) as file:
        lines = file.readlines()
    status, token_id = "NOT MINTED", "?"
    path = f"{component_id.component_type}/{component_id.author}/{component_id.name}"
    for line in lines:
        if path in line and line.split("-")[0].isnumeric():
            status = "MINTED"
            token_id = line.split("-")[0]
            break
    return status, token_id


# we have an additional command for generate-all that will generate all the metadata for the packages.
# we will need to read in the packages.json file and then generate the metadata for each package.
# we will need to check if the package is already minted.


metadata.add_command(generate)
metadata.add_command(validate)

if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
