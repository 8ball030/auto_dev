#! /usr/bin/env bash

set -euo pipefail

source scripts/demos/base.sh

gum format "Creating a new agent from an fsm"
gum format """
This will create a agent from an fsm and add it to the project.
"""

# We wait for 5 seconds before executing the command.
sleep $SLEEP_TIME

call_and_wait "adev create_from_fsm author/$AGENT_NAME auto_dev/data/fsm/samples/fsm_specification.yaml"