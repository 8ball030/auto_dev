set -e 

# fetch the agent from the local package registry
aea fetch $1 --local --alias agent

# go to the new agent
cd agent

# create and add a new ethereum key
aea generate-key ethereum && aea add-key ethereum

# install any agent deps
aea install

# issue certificates for agent peer-to-peer communications
aea issue-certificates

# finally, run the agent
aea run
