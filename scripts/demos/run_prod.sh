# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh

export SLEEP_TIME=0
sleep $SLEEP_TIME

gum format """
we have the agent service in the local packages directory.
Lets run it in production mode.
"""
sleep $SLEEP_TIME
call_and_wait "tree -L 3 packages/author" $SLEEP_TIME

call_and_wait "adev run prod author/$AGENT_NAME" 4






