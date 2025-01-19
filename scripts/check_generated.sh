#!/bin/bash

set -euo pipefail

echo "Solving dependencies"

poetry install || poetry lock --no-update

echo 'Generating lock files for template repos'
echo 'doing autonomy'
REPO_NAME="test_repo"
poetry run adev repo scaffold $REPO_NAME -t autonomy --force --auto-approve --no-install
cd $REPO_NAME
poetry lock --no-cache && poetry install
cp poetry.lock ../auto_dev/data/repo/templates/autonomy/
cd ../
rm -rf $REPO_NAME
echo 'done autonomy'

echo 'doing python'
REPO_NAME="test_repo"
poetry run adev repo scaffold $REPO_NAME -t python
cd $REPO_NAME
poetry lock --no-cache && poetry install
cp poetry.lock ../auto_dev/data/repo/templates/python/
cd ../
rm -rf $REPO_NAME
echo 'done python'

