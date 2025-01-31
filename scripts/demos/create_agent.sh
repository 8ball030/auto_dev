# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh
gum format """
We can now create a new agent for our project.
This will create an agent with the name '$AGENT_NAME'.
The agent will be published in the local packages directory 
"""
sleep $SLEEP_TIME

create_new_agent

gum format """
Now, we already have our new agent!
We can see it in the local packages directory.
"""
tree -L 3 packages/author




