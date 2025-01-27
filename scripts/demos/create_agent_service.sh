# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh

gum format """
In order to generate the agent service, for production, 
we need to convert and agent to a service with the following:
"""

sleep $SLEEP_TIME
create_new_agent

call_and_wait "adev convert agent-to-service author/$AGENT_NAME author/$AGENT_NAME " 3

gum format """
we now have the agent service in the local packages directory.
We can see this as so;
"""
sleep $SLEEP_TIME
call_and_wait "tree -L 3 packages/author" 3






