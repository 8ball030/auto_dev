# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh

gum format """
We can generate a contract from any deployed verified contract.
This is done by using the following command;

"""
sleep $SLEEP_TIME
call_and_wait "adev scaffold contract author/balancer_vault --address 0xBA12222222228d8Ba445958a75a0704d566BF2C8 --network optimism" 3

gum format """
we now have extracted all read, write and events from the deployed contract.
We can see view the generated contract in the local packages directory.
"""
sleep $SLEEP_TIME
call_and_wait "tree -L 3 packages/author/contracts" 3






