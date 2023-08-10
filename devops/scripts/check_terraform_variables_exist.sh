#!/bin/bash

# Find all directories in the repository that contain a file named "variables.tf", excluding any directories named ".terraform"
directories=$(find . -type d -not -path '*/.terraform/*' -exec test -e "{}/variables.tf" ';' -print | sort)

for dir in $directories; do
    # Check if the directory is nested in a directory that contains a "variables.tf" file
    if ! (echo "$dir" | grep -q "/.*/.terraform/.*" && echo "$dir" | grep -q "/.terraform/.*"); then
        # Check if the "variables.tf" file contains a variable named "tags"
        if grep -q "variable \"tags\"" "$dir/variables.tf"; then
            continue
        fi

        # Check if the parent directory contains a "variables.tf" file
        parent_dir=$(dirname "$dir")
        if [ -e "$parent_dir/variables.tf" ]; then
            continue
        fi

        # Check if the parent's parent directory contains a "variables.tf" file
        grandparent_dir=$(dirname "$parent_dir")
        if [ -e "$grandparent_dir/variables.tf" ]; then
            continue
        fi

        # If the script has not continued, print an error message
        echo "Error: $dir does not contain a \"tags\" variable in variables.tf"
    fi

done
