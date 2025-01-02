# CLI Commands Reference

This page provides a comprehensive reference for all available CLI commands in auto_dev.

## Core Commands

### create
Create a new agent from a template.

```bash
adev create -t <template> <author/agent_name>
```

Options:
- `-t, --template`: Template to use (required)
- `-f, --force`: Force overwrite of existing agent
- `-p, --publish`: Publish agent to local registry (default: true)
- `-c, --clean-up`: Clean up agent after creation (default: true)

Example:
```bash
adev create -t eightballer/frontend_agent new_author/new_agent
```

### scaffold
Generate various components for your agent.

#### scaffold contract
```bash
adev scaffold contract [--address ADDRESS] [--from-file FILE] [--from-abi FILE] [name]
```

Options:
- `--address`: Contract address (default: null address)
- `--from-file`: File containing addresses and names
- `--from-abi`: ABI file to scaffold from
- `--read-functions`: Comma-separated list of read functions
- `--write-functions`: Comma-separated list of write functions
- `--block-explorer-url`: Block explorer API URL (default: https://api.etherscan.io/api)
- `--block-explorer-api-key`: Block explorer API key

Example:
```bash
# Scaffold from ABI file
adev scaffold contract --from-abi contract.abi --name MyContract

# Scaffold from block explorer
adev scaffold contract --address 0x123... --name MyContract --block-explorer-api-key KEY
```

#### scaffold fsm
Scaffold a Finite State Machine (FSM) for your agent.

```bash
adev scaffold fsm [--spec SPEC_FILE]
```

Options:
- `--spec`: FSM specification YAML file

Example:
```bash
adev scaffold fsm --spec fsm_specification.yaml
```

#### scaffold protocol
Generate a new protocol package.

```bash
adev scaffold protocol PROTOCOL_SPEC_PATH [--l LANGUAGE]
```

Options:
- `--l`: Language for protocol package (default: python, choices: python, golang)

Example:
```bash
adev scaffold protocol protocol_specification.yaml --l python
```

#### scaffold connection
Create a new connection for a protocol.

```bash
adev scaffold connection NAME --protocol PROTOCOL_ID
```

Options:
- `--protocol`: PublicId of the protocol (required)

Example:
```bash
adev scaffold connection my_connection --protocol author/protocol:0.1.0
```

#### scaffold handler
Generate an AEA handler from an OpenAPI 3 specification.

```bash
adev scaffold handler SPEC_FILE PUBLIC_ID [--new-skill] [--auto-confirm]
```

Options:
- `--new-skill`: Create a new skill
- `--auto-confirm`: Auto confirm all actions

Example:
```bash
adev scaffold handler api_spec.yaml author/skill:0.1.0 --new-skill
```

#### scaffold behaviour
Generate a behaviour component.

```bash
adev scaffold behaviour SPEC_FILE [--behaviour-type TYPE] [--auto-confirm]
```

Options:
- `--behaviour-type`: Type of behaviour (metrics, simple_fsm)
- `--auto-confirm`: Auto confirm all actions
- `--target-speech-acts`: Comma-separated list of speech acts to scaffold

Example:
```bash
adev scaffold behaviour spec.yaml --behaviour-type metrics
```

#### scaffold dialogues
Generate dialogue components.

```bash
adev scaffold dialogues SPEC_FILE [--dialogue-type TYPE] [--auto-confirm]
```

Options:
- `--dialogue-type`: Type of dialogue (simple)
- `--auto-confirm`: Auto confirm all actions
- `--target-speech-acts`: Comma-separated list of speech acts to scaffold

Example:
```bash
adev scaffold dialogues spec.yaml --dialogue-type simple
```

#### scaffold tests
Generate test files.

```bash
adev scaffold tests SPEC_FILE
```

Example:
```bash
adev scaffold tests test_specification.yaml
```

#### scaffold dao
Generate Data Access Object (DAO) from OpenAPI specification.

```bash
adev scaffold dao SPEC_FILE
```

Example:
```bash
adev scaffold dao openapi_spec.yaml
```

### deps
Manage dependencies between repositories.

```bash
adev deps update -p PARENT_REPO -c CHILD_REPO [--auto-confirm]
```

Options:
- `-p, --parent-repo`: Parent repository path
- `-c, --child-repo`: Child repository path
- `--auto-confirm`: Auto confirm changes

### fmt
Format code according to project standards.

```bash
adev fmt -p PATH [--changed-only]
```

Options:
- `-p, --path`: Path to code to format
- `--changed-only`: Only format changed files

### lint
Lint code according to project standards.

```bash
adev lint -p PATH [--changed-only]
```

Options:
- `-p, --path`: Path to code to lint
- `--changed-only`: Only lint changed files

### test
Run project tests.

```bash
adev test -p TEST_PATH [--watch] [--coverage-report]
```

Options:
- `-p, --path`: Path to directory to test. If not provided, will test all packages
- `-w, --watch`: Watch files for changes
- `-c, --coverage-report`: Run coverage report (default: true)

Example:
```bash
# Test specific package with coverage
adev test -p packages/eightballer/protocols/balances

# Test all packages with file watching
adev test --watch
```

### release
Manage project releases by automatically bumping versions and creating tags.

```bash
adev release [--dep-path PATH] [--verbose]
```

Options:
- `-p, --dep-path`: Path to dependency file (default: pyproject.toml)
- `--verbose`: Enable verbose output

The release command will:
1. Check if the repository is clean
2. Increment the version number
3. Create a new tag
4. Push changes to GitHub
5. Trigger GitHub Actions for PyPI publishing

### repo
Scaffold new repositories.

```bash
adev repo scaffold [--type-of-repo TYPE] [--force] [--auto-approve] [--install/--no-install] [--initial-commit/--no-commit]
```

Options:
- `--type-of-repo`: Type of repo to scaffold
- `--force`: Force overwrite existing repo
- `--auto-approve`: Auto approve all prompts
- `--install/--no-install`: Control dependency installation
- `--initial-commit/--no-commit`: Control initial commit

### improve
Improve repository structure and configuration.

```bash
adev improve --path PATH [--type-of-repo TYPE] [--author AUTHOR] [--name NAME] [--yes]
```

Options:
- `--path`: Path to repo
- `--type-of-repo`: Type of repo
- `--author`: Author name
- `--name`: Repository name
- `--yes`: Auto answer yes to all questions

### augment
Augment components with additional functionality.

#### augment logging
Add logging handlers to your AEA configuration.

```bash
adev augment logging [HANDLERS...]
```

Available handlers:
- `console`: Rich console logging handler
- `http`: HTTP logging handler for remote logging
- `logfile`: File-based logging handler

Example:
```bash
# Add console and file logging
adev augment logging console logfile

# Add all available handlers
adev augment logging all
```

#### augment connection
Add connections to your AEA configuration.

```bash
adev augment connection [CONNECTIONS...]
```

Available connections:
- `ledger`: Ethereum ledger connection
- `abci`: ABCI connection for Tendermint
- `ipfs`: IPFS connection
- `http_client`: HTTP client connection
- `http_server`: HTTP server connection
- `websocket_server`: WebSocket server connection
- `prometheus`: Prometheus metrics connection

Example:
```bash
# Add ledger and IPFS connections
adev augment connection ledger ipfs

# Add all available connections
adev augment connection all
```

#### augment customs
Augment customs components with OpenAPI handlers.

```bash
adev augment customs openapi3 [--auto-confirm]
```

Options:
- `--auto-confirm`: Auto confirm the augmentation

## Environment Setup

To install auto_dev:

```bash
pip install autonomy-dev[all]
```

For development setup:
1. Clone the repository
2. Install dependencies: `pip install -e .[all]`
3. Install pre-commit hooks: `pre-commit install`
