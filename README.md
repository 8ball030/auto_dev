# Project Status Badges

[![Code Quality](https://github.com/8ball030/auto_dev/actions/workflows/common_check.yaml/badge.svg)](https://github.com/8ball030/auto_dev/actions/workflows/common_check.yaml)
[![Documentation](https://github.com/8ball030/auto_dev/actions/workflows/github_action.yml/badge.svg)](https://github.com/8ball030/auto_dev/actions/workflows/github_action.yml)


# Autonomy Dev

Tooling to speed up open-autonomy development.

For detailed instructions please see the [Docs.](https://8ball030.github.io/auto_dev/)

## TLDR
    # Install adev
    pip install -U "autonomy-dev[all]"
    # Make a new agent
    adev create author/cool_agent
    # Run the new agent
    adev run author/cool_agent

## Requirements

- Python >= 3.10
- Poetry <= 2.0.0

## Features

- Scaffolding of new repositories
- Scaffolding of new agents
- Scaffolding of new protocols
- Scaffolding of new contracts
- Linting and formatting tools
- Dependency management tools
- Test suite scaffolding

### Creating New Github Projects
We can make an autonomy repo
```bash
adev repo scaffold fun_new_hack
cd fun_new_hack
```

Which gives us a new repository fully setup to develop an autonomy project.
We also install dependencies
The expected output is as below.

```output
INFO     Starting Auto Dev v0.2.84 ...                                                                                                                                           
INFO     Creating a new autonomy repo.                                                                                                                                           
Scaffolding autonomy repo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
INFO     Installing host deps. This may take a while!                                                                                                                            
INFO     Initialising autonomy packages.                                                                                                                                         
INFO     Autonomy successfully setup. 
```

### Creating a new Agent

Once we have a new project, we can build new agents from templates (The `--help` command will display the available templates.

```
adev create author/cool_agent
```

By default, we provide a simple server with ping pong via websockets available at localhost:5555

```bash
# run the agent and verify the endpoint
adev run author/cool_agent
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

We provide tools to scaffold smart contract components from existing deployed contracts. The scaffolding process includes:

- Complete open-aea contract component
- Contract class with auto-generated methods
- Test suite scaffolding
- Type hints and documentation

Basic usage:
```bash
adev scaffold contract <NAME> --address <CONTRACT_ADDRESS> --network <NETWORK_NAME>
```

Example using Base:
```bash
# Scaffold USDC contract from Base
adev scaffold contract usdc \
    --address 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913 \
    --network base
```

Additional options:
```bash
# Scaffold from local ABI file
adev scaffold contract my_contract \
    --address 0xContract_Address \
    --from-abi ./path/to/abi.json \
    --network ethereum-mainnet

# Specify read/write functions
adev scaffold contract my_contract \
    --address 0xContract_Address \
    --read-functions "balanceOf,totalSupply" \
    --write-functions "transfer,approve" \
    --network polygon-mainnet
```

## Release

```bash
checkout main
git pull
adev release
```



# Test Coverage
```plaintext
<!-- Pytest Coverage Comment:Begin -->
Name                             Stmts   Miss  Cover   Missing
--------------------------------------------------------------
auto_dev/__init__.py                 0      0   100%
auto_dev/base.py                    60     19    68%   66-88
auto_dev/check_dependencies.py     236    236     0%   28-452
auto_dev/cli.py                      4      1    75%   9
auto_dev/cli_executor.py            68     36    47%   33-61, 79, 83, 87-89, 92-94, 99-105
auto_dev/constants.py               25      0   100%
auto_dev/enums.py                   36      0   100%
auto_dev/exceptions.py               5      0   100%
auto_dev/fmt.py                     59     43    27%   16-17, 21-22, 27-45, 50, 60-61, 66-80, 85-97, 102-112
auto_dev/lint.py                     7      3    57%   13-27
auto_dev/local_fork.py              52     32    38%   32-33, 37-54, 58-95
auto_dev/test.py                    16     13    19%   4, 16-39
auto_dev/utils.py                  251    153    39%   76-77, 81, 94-101, 106-151, 167, 180-185, 204-228, 233, 240-242, 247, 252, 257-269, 276-281, 290-293, 298-318, 323-337, 342-348, 370-372, 381, 388-416
--------------------------------------------------------------
TOTAL                              819    536    35%
<!-- Pytest Coverage Comment:End -->
```

## Documentation

### Running Docs Locally

To run and preview the documentation locally:

```bash
# Install mkdocs and required dependencies
pip install mkdocs-material mkdocstrings[python] mkdocs-include-markdown-plugin mkdocs-mermaid2-plugin

# Serve the documentation (available at http://127.0.0.1:8000)
mkdocs serve
```

This will start a local server and automatically reload when you make changes to the documentation.
