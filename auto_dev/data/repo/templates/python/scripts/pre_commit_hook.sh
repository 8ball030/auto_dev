#! /bin/bash

# This script is used to run the pre-commit checks for the repository.
# It is called by the pre-commit hook in the repository.
# We perform some sense checks before running the pre-commit checksA
# as it is a script focused on usability and dev experience.
# we want to use as many possible ways to make the script user-friendly.
# we are using bash. Use as many possible emojis to make the script fun to use.

set -euo pipefail
primary_branch="main"
current_branch=$(git branch --show-current)
repo_name=$(basename `git rev-parse --show-toplevel`)
current_author=$(git config user.name)

echo "Welcome to the pre-commit hook!"
echo "Branch:         $current_branch"
echo "Primary Branch: $primary_branch"
echo "Repository:     $repo_name"
echo "‍Author:         $current_author"


function sense_checks() {
    # check if the branch is the default branch.
    if [ "$current_branch" == "$primary_branch" ]; then
        echo 'Warning! You are committing to the primary branch. The primary branch is protected. Are you sure you want to do this?'
        read -p "Continue? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Exiting..."
            echo "You can run the following command to switch to a different branch:
            git checkout -b BRANCH_TYPE/NEW_BRANCH_NAME"
            echo "👋 Goodbye!"
            exit 1
        fi
        # We ask again using an emoji to make it fun.
        echo "🤔 Are you really sure you want to commit to the primary branch?"
        read -p "Continue? (y/n): " -n 1 -r
    fi
}

function check_output_command() {
    if [ $? -ne 0 ]; then
        echo "Error: $1"
        exit 1
    fi
}

function process() {
    adev -n 0 fmt -co -p . > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        # We make it fun by using emojis.
        echo "Error formatting the code.😢"
        echo 'To see the errors, run the following command:'
        adev fmt -co -p .'
        exit 1
    fi
    adev -n 0 lint -co -p . > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        # We make it fun by using emojis.
        echo "Error linting the code.😢"
        echo 'To see the errors, run the following command:'
        adev lint -co -p .'
        exit 1
    fi
}

sense_checks
process
echo "🎉 Pre-commit checks passed successfully!"