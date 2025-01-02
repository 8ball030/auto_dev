# Deployment Guide

This guide covers different deployment scenarios for auto_dev projects, from local development to production environments.

## Local Development

### Prerequisites
- Python 3.11+ (via pyenv)
- Poetry for dependency management
- Git for version control

### Setup Steps

1. Clone and set up the repository:
   ```bash
   git clone https://github.com/8ball030/auto_dev.git
   cd auto_dev
   ```

2. Install dependencies:
   ```bash
   pip install -e .[all]
   ```

3. Configure environment variables:
   ```bash
   export BLOCK_EXPLORER_API_KEY=your_api_key
   # Optional: Custom block explorer URL
   export BLOCK_EXPLORER_URL="https://api-goerli.arbiscan.io"
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Development Server
For local development and testing:

1. Run formatting:
   ```bash
   poetry run adev fmt -p .
   ```

2. Run linting:
   ```bash
   poetry run adev lint -p .
   ```

3. Run tests:
   ```bash
   poetry run adev test -p tests
   ```

## Production Deployment

### System Requirements
- Linux-based OS (Ubuntu 20.04+ recommended)
- Python 3.11+
- Sufficient disk space for dependencies
- Network access for API calls

### Installation Steps

1. Create a dedicated user (optional but recommended):
   ```bash
   sudo useradd -m -s /bin/bash autodev
   sudo su - autodev
   ```

2. Install system dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-venv git
   ```

3. Install auto_dev:
   ```bash
   pip install autonomy-dev[all]
   ```

4. Set up environment variables (add to ~/.bashrc):
   ```bash
   echo 'export BLOCK_EXPLORER_API_KEY="your_api_key"' >> ~/.bashrc
   echo 'export BLOCK_EXPLORER_URL="your_explorer_url"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Service Configuration
For running auto_dev components as services:

1. Create a systemd service file:
   ```ini
   [Unit]
   Description=Auto Dev Service
   After=network.target

   [Service]
   Type=simple
   User=autodev
   Environment=BLOCK_EXPLORER_API_KEY=your_api_key
   Environment=BLOCK_EXPLORER_URL=your_explorer_url
   WorkingDirectory=/home/autodev/auto_dev
   ExecStart=/usr/local/bin/adev your_command
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

2. Enable and start the service:
   ```bash
   sudo systemctl enable autodev
   sudo systemctl start autodev
   ```

### Monitoring
Monitor your deployment using:
```bash
sudo systemctl status autodev
journalctl -u autodev -f
```

## Docker Deployment (Optional)

While auto_dev doesn't currently provide official Docker images, you can containerize your auto_dev projects using this example configuration:

1. Create a Dockerfile:
   ```dockerfile
   FROM python:3.11-slim

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       git \
       && rm -rf /var/lib/apt/lists/*

   # Install auto_dev
   RUN pip install autonomy-dev[all]

   # Set working directory
   WORKDIR /app

   # Copy your project files
   COPY . .

   # Set environment variables
   ENV BLOCK_EXPLORER_API_KEY=your_api_key
   ENV BLOCK_EXPLORER_URL=your_explorer_url

   # Run your command
   CMD ["adev", "your_command"]
   ```

2. Build and run:
   ```bash
   docker build -t auto_dev .
   docker run -e BLOCK_EXPLORER_API_KEY=your_key auto_dev
   ```

### Docker Compose
For more complex setups, use docker-compose:

```yaml
version: '3'
services:
  auto_dev:
    build: .
    environment:
      - BLOCK_EXPLORER_API_KEY=${BLOCK_EXPLORER_API_KEY}
      - BLOCK_EXPLORER_URL=${BLOCK_EXPLORER_URL}
    volumes:
      - .:/app
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip install -e .[all]  # Reinstall with all optional dependencies
   ```

2. **Environment Variables**
   ```bash
   # Verify environment variables
   echo $BLOCK_EXPLORER_API_KEY
   echo $BLOCK_EXPLORER_URL
   ```

3. **Service Issues**
   ```bash
   # Check service logs
   journalctl -u autodev -n 100
   ```

### Getting Help
- Check the [installation guide](installation.md) for setup issues
- Review the [usage guide](usage.md) for command usage
- Submit issues on [GitHub](https://github.com/8ball030/auto_dev/issues)
