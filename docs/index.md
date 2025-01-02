# Project Status Badges

[![Code Quality](https://github.com/8ball030/auto_dev/actions/workflows/common_check.yaml/badge.svg)](https://github.com/8ball030/auto_dev/actions/workflows/common_check.yaml)


# Autonomy Dev

Tooling to speed up open-autonomy development.


## TLDR

```bash
# install 
pip install autonomy-dev[all]
```

```bash
# create a repo & a simple webserver agent
adev repo scaffold fun_new_hack && \
cd fun_new_hack && \
adev create author/cool_agent \
    -t eightballer/frontend_agent # type of template to use.
# sync to the local registry.
yes 'third_party' | autonomy packages lock

```

## Documentation

For detailed information about using auto_dev, check out our documentation:

- [Installation Guide](installation.md) - Complete setup instructions and environment configuration
- [Usage Guide](usage.md) - Detailed examples and common workflows
- [CLI Reference](commands/index.md) - Comprehensive command-line interface documentation
- [Deployment Guide](deployment.md) - Instructions for local and production deployments

For development setup and contribution guidelines, see the [Installation Guide](installation.md#development-setup).

### Local Documentation

To run the documentation locally:
1. Follow the [documentation setup guide](installation.md#running-documentation-locally)
2. Visit `http://127.0.0.1:8000/` in your browser
3. Documentation will auto-reload as you make changes

## Development

For development tools and workflows:
- [Code Formatting](usage.md#development-workflow) - Learn about code formatting standards
- [Testing](usage.md#development-workflow) - Running and writing tests
- [Contributing](contributing.md) - Guidelines for contributing
- [Deployment](deployment.md) - Setting up development environments

## Usage Examples

Check out these guides for common use cases:
- [Quick Start](usage.md#quick-start-guide) - Get started quickly
- [Protocol Scaffolding](usage.md#common-workflows) - Generate protocol components
- [Contract Integration](usage.md#common-workflows) - Work with smart contracts
- [Development Tools](installation.md#development-tools) - Available development tools

```bash
# run the agent and verify the endpoint

```


## Usage

There are a number of useful command tools available.

- Dev Tooling:
    A). linting `adev lint`
    B). formatting `adev fmt`
    C). dependency management `adev deps update`

- Scaffolding: Tooling to auto generate repositories and components.


### Create

- Templated agents for speedy proof of concept and getting started fast.


### Scaffolding of Components

#### Protocols

We provide tools to generate protocols components from specs.

```bash
adev create author/tmp_agent_name -t eightballer/base --force
cd tmp_agent_name
adev scaffold protocol ../specs/protocols/balances.yaml 
aea -s publish --push-missing
...
Starting Auto Dev v0.2.75 ...
Using 32 processes for processing
Setting log level to INFO
Creating agent tmp_agent_name from template eightballer/base
Executing command: ['poetry', 'run', 'autonomy', 'fetch', 'bafybeidohldv57m3jkc33zpgbxukaushmcibmt4ncnsnomd3pvpocxs3ui', '--alias', 'tmp_agent_name']
Command executed successfully.
Agent tmp_agent_name created successfully.
Starting Auto Dev v0.2.75 ...
Using 32 processes for processing
Setting log level to INFO
Read protocol specification: ../specs/protocols/balances.yaml
protolint version 0.50.0(d6a3250)
protolint version 0.50.0(d6a3250)
Updated: /home/eight/Projects/StationsStation/repos/capitalisation_station/tmp_agent_name/protocols/balances/custom_types.py
New protocol scaffolded at /home/eight/Projects/StationsStation/repos/capitalisation_station/tmp_agent_name/protocols/balances

...
# Tests can be run as well;
adev test -p packages/eightballer/protocols/balances
Testing path: `packages/eightballer/protocols/balances/` ⌛
Testing... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0% -:--:--👌 - packages/eightballer/protocols/balances/
Testing... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:02
Testing completed successfully! ✅
```

#### Contracts

We can scaffold a new contract using the `adev scaffold contract` command. This will create a new directory with;
- open-aea contract component
    - open-aea contract component class 🎉
    - open-aea contract component function generation 🚧
    - open-aea contract component test generation 🚧


```bash
adev scaffold contract 0xc939df369C0Fc240C975A6dEEEE77d87bCFaC259 beyond_pricer \
      --block-explorer-api-key $BLOCK_EXPLORER_API_KEY \
      --block-explorer-url "https://api-goerli.arbiscan.io"
```


## Installation

```bash
pip install autonomy-dev[all]
```
## Release

```bash
checkout main
git pull
adev release
```
