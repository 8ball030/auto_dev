#! /bin/bash
set -e

if [[ "$#" -lt 1 ]]; then
    echo "Usage: $0 <author/agent_name> [--force] [--debug]"
    echo "  <author/agent_name>: Identifier for the agent (e.g., eightballer/donation_station)"
    echo "  --force            : Remove existing build directory if it exists"
    echo "  --debug            : Run the agent in DEBUG mode"
    exit 1
fi

# Initialize variables
FORCE=false
DEBUG=false
AGENT_IDENTIFIER=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --force)
            FORCE=true
            ;;
        --debug)
            DEBUG=true
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Usage: $0 <author/agent_name> [--force] [--debug]"
            exit 1
            ;;
        *)
            if [[ -z "$AGENT_IDENTIFIER" ]]; then
                AGENT_IDENTIFIER="$1"
            else
                echo "Multiple agent identifiers provided."
                echo "Usage: $0 <author/agent_name> [--force] [--debug]"
                exit 1
            fi
            ;;
    esac
    shift
done

agent_author=$(echo "$AGENT_IDENTIFIER" | cut -d'/' -f1)
agent_name=$(echo "$AGENT_IDENTIFIER" | cut -d'/' -f2)


echo "   Agent author: $agent_author"
echo "   Agent name:   $agent_name"

CWD=$(pwd)
BUILD_DIR="build"
AGENT_BUILD_DIR="$BUILD_DIR/$agent_author/$agent_name"

# Handle existing build directory
if [[ -d "$AGENT_BUILD_DIR" ]]; then
    if [[ "$FORCE" == true ]]; then
        echo "Removing existing build directory '$AGENT_BUILD_DIR' due to --force."
        rm -rf "$AGENT_BUILD_DIR"
    else
        echo "Error: Build directory '$AGENT_BUILD_DIR' already exists. Use --force to overwrite."
        exit 1
    fi
fi

# Ensure the build author directory exists
mkdir -p "$BUILD_DIR/$agent_author"

# Fetch the agent from the local package registry
echo "Fetching agent '$AGENT_IDENTIFIER' from the local package registry..."
if ! aea -s fetch "$AGENT_IDENTIFIER" --local > /dev/null; then
    echo "Error: Failed to fetch agent '$AGENT_IDENTIFIER'."
    exit 1
fi

# Move the fetched agent to the build directory
echo "Moving agent to '$AGENT_BUILD_DIR'."
mv "$agent_name" "$BUILD_DIR/$agent_author/"

# Navigate to the agent's build directory
cd "$AGENT_BUILD_DIR"

# create and add a new ethereum key
echo "Setting up Ethereum key..."
if [[ ! -f "$CWD/ethereum_private_key.txt" ]]; then
    if ! aea -s generate-key ethereum || ! aea -s add-key ethereum; then
        echo "Error: Failed to generate or add Ethereum key."
        exit 1
    fi
else
    cp "$CWD/ethereum_private_key.txt" "./ethereum_private_key.txt"
    if ! aea -s add-key ethereum; then
        echo "Error: Failed to add Ethereum key."
        exit 1
    fi
fi

# install any agent deps
echo "Installing agent dependencies..."
if ! aea -s install; then
    echo "Error: Failed to install agent dependencies."
    exit 1
fi

# issue certificates for agent peer-to-peer communications
if [[ ! -d "$CWD/certs" ]]; then
    echo "Issuing certificates for agent peer-to-peer communications..."
    if ! aea -s issue-certificates; then
        echo "Error: Failed to issue certificates."
        exit 1
    fi
else
    echo "Copying certificates from the parent directory..."
    cp -r "$CWD/certs" ./.certs
fi

# Wait for the Tendermint node to start
echo "Waiting for Tendermint node to be ready..."
tries=0
tm_started=false
while [[ "$tries" -lt 20 ]]; do
    tries=$((tries+1))
    if curl -sSf localhost:8080/hard_reset > /dev/null 2>&1; then
        echo "Tendermint node is ready."
        tm_started=true
        break
    fi
    echo "Tendermint node is not ready yet, waiting..."
    sleep 1
done

if [[ "$tm_started" == false ]]; then
    echo "Error:Tendermint node did not start in time. Please verify that the docker tendermint node is running."
    exit 1
fi

echo "Starting the agent..."

# Build the command
cmd="aea -s"
if [[ "$DEBUG" == true ]]; then
    cmd="$cmd -v DEBUG"
fi
cmd="$cmd run --env '../.env'"

# Execute the command
if ! eval "$cmd"; then
    echo "Error: Failed to start the agent."
    exit 1
fi

echo "Agent started successfully."
