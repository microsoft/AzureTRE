#!/bin/bash
# Find all .hcl files. for each, go to the containing folder and run 'terraform init --upgrade' to update the lock files. Useful when doing a cross project versions change

# Run from root folder

list="$(find . -type f -name "*.hcl")"

for i in $list
do
    rm $i
    echo "Updating lock file" + $i
    dir=$(dirname $i)
    ( cd "$dir" && terraform init -upgrade=true -backend=false )
done
