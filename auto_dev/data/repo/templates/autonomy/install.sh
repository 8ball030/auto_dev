#! /bin/bash
set -e
unset VIRTUAL_ENV && poetry -v run echo "Installing dependencies"
executable=$(echo $(echo /home/$(whoami)/.cache/pypoetry/virtualenvs/$(poetry env list |head -n 1| awk '{print $1}'))/bin/pip)
echo "Executing using :${executable}"
echo "Installing host dependencies"
${executable} install 'cython<3.0.0' pyyaml==5.4.1 --no-build-isolation -v 
echo "Done installing host dependencies"
poetry install
echo "Done installing dependencies"
