#! /bin/bash

# Run the development server



while true; do
    poetry run adev -v test -p .  -w || continue
    poetry run adev -v -n 2 fmt  -p . -co && poetry run adev -v -n 2 lint -co || continue
    # We check if there are any changes in the code
    if git diff --quiet; then
        poetry run adev -v -n 2 test -p . -co || continue
    else
        poetry run adev -v -n 2 test -p . -co || continue
        git add .
        date=$(date)
        git commit -m "Auto commit @ $date"
        git push
    fi
    sleep 2
done