# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh

gum format "Starting the demo"

create_new_agent

gum format "Demo complete"




