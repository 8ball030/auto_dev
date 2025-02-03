# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh

gum format """
We can generate a contract from any deployed verified contract.
This is done by using the following command;

    adev scaffold contract author/usdc \
        --address 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913 \
        --network base
"""
sleep $SLEEP_TIME
call_and_wait "adev scaffold contract author/balancer_vault --address 0x833589fcd6edb6e08f4c7c32d4f71b54bda02913 --network base" 4

gum format """
we now have extracted all read, write and events from the deployed contract.
We can see view the generated contract in the local packages directory.
"""
sleep $SLEEP_TIME
call_and_wait "tree -L 3 packages/author/contracts" 3






