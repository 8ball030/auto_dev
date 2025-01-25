#! /usr/bin/env bash

set -euo pipefail

source scripts/demos/base.sh

gum format "Creating a new project"
gum format """
This will create a new repository with 
the name $DEMO_PROJECT_NAME.
The repository will contain a basic 
structure for an autonolas project.
This includes the following;

1. A basic structure for the agent project.

2. basic structure for the ci/cd.          

3. Development tools for rapid development.

4. Dependency management for olas projects."""

# We wait for 5 seconds before executing the command.
sleep $SLEEP_TIME

create_new_project

gum format """
We now have a new project called $DEMO_PROJECT_NAME.
We can now navigate to the project and start developing our project.
This creates a new project with the following structure:
"""
sleep $SLEEP_TIME
call_and_wait "tree -L 2 ./$DEMO_PROJECT_NAME" $SLEEP_TIME