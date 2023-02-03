#!/bin/bash
set -e

# if no arguments are provided, return usage function
if [[ $# -ne 2 || -z $1 || -z $2 ]]; then
    echo "Usage: $0 <left_plan_file> <right_plan_file>"
    exit 1
fi

left_tfplan=$1
right_tfplan=$2

echo "Comparing ${left_tfplan} to ${right_tfplan}..."


function plan_change() {
  terraform show -json "$1" | jq -r '.resource_changes[] | select(.change.actions[] | contains("no-op") or contains("read") | not)' > "$1_filtered.json"
}

plan_change "${left_tfplan}"
plan_change "${right_tfplan}"

diff <(jq --sort-keys . "${left_tfplan}"_filtered.json) <(jq --sort-keys . "${right_tfplan}"_filtered.json)
