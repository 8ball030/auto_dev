#! /bin/env bash

set -euo pipefail

export GUM_FORMAT_TYPE="markdown"
export GUM_FORMAT_THEME="dark"

export SLEEP_TIME=4
export DEMO_PROJECT_NAME="fun_hackathon"
export AGENT_NAME="fun_agent"

export REAL_WORKING_DIR=$(pwd)
export SIMULATED_WORKING_DIR="~/"


function call_and_wait() {
    # echo '{{Bold "Executing"}} "adev repo scaffold fun_hackathon"' | gum format -t template
    # echo "Executing '$1'" | gum format -t template
    simulate_terminal_with_command "$1"
    sleep $2
    # We now clear the screen
    echo -e "\033[2J\033[3J\033[H"
}

# we format running a command like a terminal

function clear_screen() {
    printf "\033c"      # Reset terminal (equivalent to clearing the screen fully)
    printf "\033[H"     # Move cursor to the home position
    printf "\033[J"     # Clear from the cursor to the end of the screen
    
    # Optionally, send additional escape sequences
    echo -e "\033[2J\033[3J\033[H"  # Full clear
    
    # Simulate the command prompt with the given command
}

function simulate_terminal_with_command() {
    clear_screen
    # Simulate terminal appearance
    local user="user"
    local host="host"
    local cwd=$(echo $(pwd) | sed "s|$REAL_WORKING_DIR|$SIMULATED_WORKING_DIR|g")
    # we replace the real working directory with the simulated working directory

    
    # Display a simulated terminal prompt
    echo -e "\033[1;34m${user}@${host}\033[0m:\033[1;36m${cwd}\033[0m$ \033[1;32m$1\033[0m"
    eval $1
    echo -e "\033[1;34m${user}@${host}\033[0m:\033[1;36m${cwd}\033[0m$"
    echo ""
}


function create_new_project(){
    # We clean up the project
    rm -rf $DEMO_PROJECT_NAME
    call_and_wait "adev repo scaffold $DEMO_PROJECT_NAME" $SLEEP_TIME
}

function create_new_agent() {
    gum format "Creating a new agent."
    gum format """
    We can now create a new agent for our project.
    This will create an agent with the name '$AGENT_NAME'.
    The agent will be published in the local packages directory 
    """
    sleep $SLEEP_TIME
    call_and_wait "adev create author/$AGENT_NAME" $SLEEP_TIME

    # # We convert to a service
    # call_and_wait "adev convert agent-to-service author/$AGENT_NAME author/cool_service" $SLEEP_TIME

    sleep $SLEEP_TIME
}

