# We use gum to create a pretty demo for the cli tool.
# https://github.com/charmbracelet/gum?tab=readme-ov-file
# This is the source of the demo within the readme.

#! /bin/env bash

set -euo pipefail

source scripts/demos/base.sh
gum format """
Protocols are the used to define the structure of the messages
that components and agents will use to communicate with each other.

Luckily, we can create a new use adev to create a new protocol from a spec file.

Not only that, but we can will also verify;

- The protocol is valid
- The protocol is well-formed
- The generated tests pass.

"""
sleep $SLEEP_TIME

call_and_wait "adev wf  auto_dev/data/workflows/create_new_protocol_from_spec.yaml" 1

call_and_wait "tree -L 3 packages/eightballer/protocols/balances" 3




