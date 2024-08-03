set -e 

# fetch the agent from the local package registry
echo "Fetching agent $1 from the local package registry..."
aea -s fetch $1 --local > /dev/null

# go to the new agent
# n the format eightballer/automation_station, we need to split by / nad go into the second part

agent_name=$(echo $1 | cut -d'/' -f2)
agent_author=$(echo $1 | cut -d'/' -f1)

echo "   Agent author: $agent_author"
echo "   Agent name:   $agent_name"

cd $agent_name


# create and add a new ethereum key
if [ ! -f ../ethereum_private_key.txt ]; then
    aea -s generate-key ethereum && aea -s add-key ethereum
else
    cp ../ethereum_private_key.txt ./ethereum_private_key.txt
    aea -s add-key ethereum 
fi
# install any agent deps
aea -s install

# issue certificates for agent peer-to-peer communications
if [ ! -f ../certs ]; then
    aea -s issue-certificates
else
    cp -r ../certs ./
fi

# finally, run the agent
aea -s run
