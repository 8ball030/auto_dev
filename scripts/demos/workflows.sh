#!/usr/bin/env bash
set -eu pipefail

source scripts/demos/base.sh

gum format "Running workflows!"
call_and_wait "poetry run adev wf auto_dev/data/workflows/fmt_lint_workflow.yaml" 3
