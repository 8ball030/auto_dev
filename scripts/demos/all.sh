#! /usr/env bash
export DEMO_PROJECT_NAME="fun_hackathon"
export AGENT_NAME="fun_agent"

set -euo pipefail


bash scripts/demos/cast.sh docs/assets/workflows.gif  scripts/demos/workflows.sh

bash scripts/demos/cast.sh docs/assets/create_repo.gif scripts/demos/create_new_repo.sh
bash scripts/demos/cast.sh docs/assets/create_agent.gif scripts/demos/create_agent.sh
rm -rf packages
bash scripts/demos/cast.sh docs/assets/create_agent_service.gif scripts/demos/create_agent_service.sh

rm -rf $DEMO_PROJECT_NAME
rm -rf packages