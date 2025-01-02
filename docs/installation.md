# Installation Guide

## Quick Install

For users who just want to use auto_dev, install via pip:

```console
$ pip install autonomy-dev[all]
```

This installs the latest stable release with all optional dependencies.

### Quick Start Example

```bash
# Create a repo & a simple webserver agent
adev repo scaffold fun_new_hack && \
cd fun_new_hack && \
adev create author/cool_agent \
    -t eightballer/frontend_agent # type of template to use

# Sync to the local registry
yes 'third_party' | autonomy packages lock
```

## Development Setup

For developers who want to contribute or modify the code:

1. Set up Python environment (Python 3.11+ recommended):
   ```console
   # Install pyenv if needed
   curl https://pyenv.run | bash
   
   # Install Python 3.11
   pyenv install 3.11
   pyenv global 3.11
   ```

2. Clone the repository:
   ```console
   git clone https://github.com/8ball030/auto_dev.git
   cd auto_dev
   ```

3. Install development dependencies:
   ```console
   pip install -e .[all]
   ```

4. Set up pre-commit hooks:
   ```console
   pre-commit install
   ```

## Repository Structure

Key directories:
- `auto_dev/`: Core functionality
  - `commands/`: CLI tools implementation
  - `contracts/`: Contract-related functionality
  - `dao/`: Data Access Object generation
  - `handlers/`: Message handling components
  - `protocols/`: Protocol scaffolding
  - `behaviours/`: Agent behavior definitions
  - `fsm/`: Finite State Machine management
  - `data/`: Templates and configuration files

## Development Tools

The repository uses several development tools:

1. **Poetry** for dependency management
2. **pre-commit** for code quality checks
3. **pytest** for testing (current coverage: ~35%)
4. **mkdocs** for documentation

## Running Documentation Locally

To run and develop the documentation locally:

1. Install documentation dependencies:
   ```console
   pip install mkdocs-material mkdocs-include-markdown-plugin mkdocstrings[python] mkdocs-autorefs
   ```

2. Serve documentation locally:
   ```console
   mkdocs serve
   ```
   This will start a development server at `http://127.0.0.1:8000/`

3. Build documentation (optional):
   ```console
   mkdocs build
   ```
   This generates static files in the `site/` directory

The documentation will auto-reload when you make changes to the markdown files.

### Environment Variables

Some features require environment variables:

1. **Block Explorer Integration**:
   ```bash
   export BLOCK_EXPLORER_API_KEY=your_api_key
   # Optional: Custom block explorer URL
   export BLOCK_EXPLORER_URL="https://api-goerli.arbiscan.io"
   ```

### Development Commands

```bash
# Format code
poetry run adev -n 0 fmt -p . -co

# Lint code
poetry run adev -v -n 0 lint -p . -co

# Run tests
poetry run adev -v test -p tests

# Test specific components
adev test -p packages/eightballer/protocols/balances

# Release process
git checkout main
git pull
adev release
```

## Troubleshooting

Common issues and solutions:

1. **Missing dependencies**:
   ```console
   pip install -e .[all]  # Reinstall with all optional dependencies
   ```

2. **Pre-commit hook failures**:
   ```console
   pre-commit run --all-files  # Run all checks manually
   ```

3. **Python version conflicts**:
   ```console
   pyenv install 3.11  # Install correct Python version
   pyenv local 3.11    # Set local Python version
   ```

[pip]: https://pip.pypa.io
[Python installation guide]: http://docs.python-guide.org/en/latest/starting/installation/
