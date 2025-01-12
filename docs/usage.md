# Usage

## Installation

> **Note:** Python version 3.11 or higher is required.

To use auto_dev in a project, first install it via pip:

```bash
pip install autonomy-dev[all]
```

## Basic Commands

### Repository and Agent Creation

Create a new repository and agent:

```bash
# Create a new repository
adev repo scaffold fun_new_hack

# Navigate to the repository
cd fun_new_hack

# Create an agent using a template
adev create author/cool_agent --template eightballer/frontend_agent

# Optional: Sync to local registry
yes 'third_party' | autonomy packages lock

adev run author/cool_agent
```

### Development Tools

Auto_dev provides several development utilities:

1. **Linting**
```bash
adev lint
```

2. **Formatting**
```bash
adev fmt
```

3. **Dependency Management**
```bash
adev deps update
```

## Component Scaffolding

### Protocol Generation

Generate protocol components from specifications:

```bash
# Create a base agent first
adev create author/tmp_agent_name -t eightballer/base --force

# Navigate to agent directory
cd tmp_agent_name

# Scaffold protocol from spec file
adev scaffold protocol ../specs/protocols/balances.yaml 

# Publish the protocol
aea -s publish --push-missing

# Run tests for the protocol
adev test -p packages/eightballer/protocols/balances
```

### Contract Scaffolding

Generate smart contract components from deployed contracts:

```bash
# Basic usage
adev scaffold contract <NAME> --address <CONTRACT_ADDRESS> --network <NETWORK_NAME>

# Example: Scaffold USDC contract from Base network
adev scaffold contract usdc --address 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913 --network base

# Advanced usage with local ABI
adev scaffold contract my_contract \
    --address 0xContract_Address \
    --from-abi ./path/to/abi.json \
    --network ethereum-mainnet

# Specify specific functions to include
adev scaffold contract my_contract \
    --address 0xContract_Address \
    --read-functions "balanceOf,totalSupply" \
    --write-functions "transfer,approve" \
    --network polygon-mainnet
```

## Release Process

To create a new release:

```bash
# Ensure you're on main branch
checkout main
git pull

# Create release
adev release
```
