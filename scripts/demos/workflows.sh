#!/usr/bin/env bash
set -eu pipefail

poetry run adev wf  auto_dev/data/workflows/fmt_lint_workflow.yaml
