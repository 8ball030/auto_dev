#! /bin/bash

set -euo pipefail

REPO="8ball030/auto_dev"

function check_poetry_deps() {
    echo "Checking if poetry dependencies are up to date"
    poetry update  && \
        poetry lock  && \
        poetry install
}


function create_new_branch() {
    # Create a new branch
    date=$(date '+%Y-%m-%d-%H-%M-%S')
    git checkout -b deps/update-poetry-deps-$date
    git add pyproject.toml poetry.lock
    git commit -m "Update poetry dependencies to latest versions using 'poetry update && poetry lock && poetry install'"
    git push origin deps/update-poetry-deps-$date
    echo "New branch created: deps/update-poetry-deps-$date"
    gh pr create -B main  -R $REPO --fill -t "[deps] Update poetry dependencies to latest versions" -b "Update poetry dependencies to latest versions"
}


function main() {
    check_poetry_deps
    if check_if_deps_are_now_dirty; then
        create_new_branch
    fi
}

function check_if_deps_are_now_dirty() {
    # Check if the pyproject.toml or the poetry.lock files are dirty
    if git diff --exit-code pyproject.toml poetry.lock; then
        echo "No changes detected in pyproject.toml or poetry.lock"
        return 1
    else
        echo "Changes detected in pyproject.toml or poetry.lock"
        return 0
    fi
}

main
