#!/bin/bash

set -euo pipefail

echo "Solving dependencies"

echo 'Generating lock files for template repos'
echo 'doing autonomy'
REPO_NAME="test_repo"
poetry run adev repo scaffold $REPO_NAME -t autonomy --force --auto-approve --no-install
cd $REPO_NAME
echo removing old env 
poetry env remove --all
echo locking
# poetry lock --no-cache -vv || exit 0
# echo installing
# poetry install
# poetry check --lock
# cp poetry.lock ../auto_dev/data/repo/templates/autonomy/
cd ../
rm -rf $REPO_NAME
echo 'done autonomy'

echo 'doing python'
REPO_NAME="test_repo"
# poetry run adev repo scaffold $REPO_NAME -t python
# cd $REPO_NAME
# poetry lock --no-cache && poetry install
# cp poetry.lock ../auto_dev/data/repo/templates/python/
cd ../
rm -rf $REPO_NAME
echo 'done python'

