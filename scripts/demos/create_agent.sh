# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh

create_new_agent

gum format """
Now, we already have our new agent!
AND We have converted it to a service ready to be deployed.
We can see it in the local packages directory.
"""
tree -L 3 packages/author




