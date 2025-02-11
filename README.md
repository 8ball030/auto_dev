# Autonomy Dev

[![Code Quality](https://github.com/8ball030/auto_dev/actions/workflows/common_check.yaml/badge.svg)](https://github.com/8ball030/auto_dev/actions/workflows/common_check.yaml)
[![Documentation](https://github.com/8ball030/auto_dev/actions/workflows/docs_build_deploy.yml/badge.svg)](https://github.com/8ball030/auto_dev/actions/workflows/github_action.yml)
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

Tooling to speed up open-autonomy development.

For detailed instructions please see the [Docs.](https://8ball030.github.io/auto_dev/)

## TLDR
    # Install adev
    pip install -U "autonomy-dev[all]"
    # Make a new agent
    adev create author/cool_agent
    # Run the new agent
    adev run dev author/cool_agent

## Requirements

- Python >= 3.10,<3.12
- Poetry >= 1.8.3
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Features

- Scaffolding of new repositories, agent, protocols, contracts, connections, skills.
- Linting and formatting tools
- Dependency management tools
- Test suite scaffolding

### Creating New Github Projects

We can make an autonomy repo
```bash
adev repo scaffold fun_new_hack
cd fun_new_hack
```

![asciicast](docs/assets/create_repo.gif)


### Creating a new Agent

Once we have a new project, we can build new agents from templates 
There are a number of templates available and the `--help` flag will display the available options.

```bash
adev create author/cool_agent
```

![asciicast](docs/assets/create_agent.gif)

By default, we provide a simple server with ping pong via websockets available at localhost:5555

```bash
# run the agent and verify the endpoint
adev run author/cool_agent
```


### Creating an Agent Service

Running agents in production requires a service to manage the agent lifecycle. We can convert an agent to a service with the following command.

```bash
adev convert agent-to-service author/agent_name author/service_name
```
![asciicast](docs/assets/create_agent_service.gif)


### Scaffolding of Components

#### Contracts

We provide tools to scaffold smart contract components from existing deployed contracts. The scaffolding process includes:

- Complete open-aea contract component
- Contract class with auto-generated methods
- Events, Read and Write methods extracted from the contract ABI.
- Type hints and documentation

```bash
# Scaffold USDC contract from Base
adev scaffold contract author/usdc \
    --address 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913 \
    --network base
```

![asciicast](docs/assets/create_contract.gif)


#### Protocols

Protocols components can be fully scaffolded from a yaml file. The scaffolding process includes:
- Protocol class with auto-generated methods
- Linted and formatted code
- Type hints and documentation
- Test Suite
- Pydantic models for custom types.


```bash
adev scaffold protocol auto_dev/data/protocols/examples/balances.yaml
```

![asciicast](docs/assets/create_protocol.gif)


## Dependency Management

For projects created with adev, updates to both:

- autonomy packages
- upstream python packages

are automated using as so;

```
adev deps verify
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

## Miscillaneous

There are a number of useful command tools available.

- Dev Tooling:
    A). linting `adev lint`
    B). formatting `adev fmt`
    C). dependency management `adev deps update`

- Scaffolding: Tooling to auto generate repositories and components.
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
