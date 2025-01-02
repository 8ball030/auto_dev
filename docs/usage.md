# Quick Start Guide

This guide will help you get started with auto_dev quickly.

## Basic Usage

1. Create a new agent:
   ```bash
   adev create -t eightballer/frontend_agent my_author/my_agent
   ```

2. Scaffold components:
   ```bash
   # Add a contract
   adev scaffold contract --from-abi contract.abi --name MyContract
   
   # Add an FSM
   adev scaffold fsm --spec fsm_spec.yaml
   ```

3. Format and lint code:
   ```bash
   # Format code
   adev fmt -p .
   
   # Lint code
   adev lint -p .
   ```

4. Run tests:
   ```bash
   adev test -p tests
   ```

## Common Workflows

### Creating a New Agent

1. Choose a template:
   ```bash
   # List available templates
   adev create --help
   
   # Create from template
   adev create -t eightballer/frontend_agent my_author/my_agent
   ```

2. Scaffold Protocol Components:
   ```bash
   # Create a temporary agent
   adev create author/tmp_agent_name -t eightballer/base --force
   cd tmp_agent_name
   
   # Generate protocol from spec
   adev scaffold protocol ../specs/protocols/balances.yaml
   
   # Publish to registry
   aea -s publish --push-missing
   ```

3. Scaffold Contract Components:
   ```bash
   # Generate contract from address
   adev scaffold contract 0xc939df369C0Fc240C975A6dEEEE77d87bCFaC259 contract_name \
         --block-explorer-api-key $BLOCK_EXPLORER_API_KEY \
         --block-explorer-url "https://api-goerli.arbiscan.io"
   ```

   This creates:
   - Open-AEA contract component class
   - Contract component function generation (in progress)
   - Contract component test generation (in progress)

### Managing Dependencies

1. Update dependencies:
   ```bash
   adev deps update -p parent_repo -c child_repo
   ```

### Development Workflow

1. Format code before committing:
   ```bash
   adev fmt -p . --changed-only
   ```


2. Run linting:
   ```bash
   adev lint -p . --changed-only
   ```

3. Run tests:
   ```bash
   adev test -p tests --coverage-report
   ```

## Advanced Scaffolding Scenarios

### Overriding Default Templates
```bash
# List available templates
adev create --help

# Create custom template
adev create my_author/custom_agent -t eightballer/base --force

# Override specific components
adev create my_author/custom_agent \
    -t eightballer/frontend_agent \
    --override-protocol my_protocol \
    --override-connection my_connection
```

### Multiple Protocol Generation
```bash
# Generate multiple protocols from specs
for spec in specs/protocols/*.yaml; do
    adev scaffold protocol "$spec"
done

# Publish all to registry
aea -s publish --push-missing
```

### Custom Contract Integration
```bash
# Generate contract with custom settings
adev scaffold contract 0xAddress contract_name \
    --block-explorer-api-key $BLOCK_EXPLORER_API_KEY \
    --block-explorer-url "https://api-goerli.arbiscan.io" \
    --custom-abi path/to/abi.json \
    --implementation-class MyCustomContract

# Generate multiple contracts
for addr in $CONTRACT_ADDRESSES; do
    adev scaffold contract "$addr" "${addr}_contract" \
        --block-explorer-api-key $BLOCK_EXPLORER_API_KEY
done
```

### Advanced FSM Workflows
```bash
# Generate FSM from complex spec
adev scaffold fsm \
    --spec complex_fsm.yaml \
    --custom-states custom_states.py \
    --transitions transitions.yaml

# Chain multiple FSMs
adev scaffold fsm-chain \
    --specs "fsm1.yaml,fsm2.yaml,fsm3.yaml" \
    --output chained_fsm.yaml
```

### Development Best Practices

1. **Code Quality**
   ```bash
   # Format only changed files
   adev fmt -p . --changed-only

   # Run specific linting checks
   adev lint -p . --select E,W,F

   # Run tests with coverage
   adev test -p tests --coverage-report
   ```

2. **Dependency Management**
   ```bash
   # Update specific dependencies
   adev deps update -p . --packages "package1,package2"

   # Check for outdated dependencies
   adev deps check -p .

   # Update all dependencies
   adev deps update -p . --all
   ```

3. **Release Process**
   ```bash
   # Prepare release
   git checkout main
   git pull
   adev release --dry-run  # Check what would be released

   # Perform release
   adev release
   ```

## Next Steps

- Check the [CLI Reference](commands/index.md) for detailed command documentation
- Explore [FSM documentation](fsm.md) for state machine development
- Read [OpenAPI guide](openapi.md) for API integration
- Review [Deployment Guide](deployment.md) for production setup
