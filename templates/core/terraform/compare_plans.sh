#!/bin/bash
set -e

function usage() {
    cat <<USAGE

    Usage: $0 [--left <plan_file> ]  [ --right <plan_file> ]

    Options:
        --left   First tfplan file to compare
        --right  Second tfplan file to compare
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

current="false"

while [ "$1" != "" ]; do
    case $1 in
    --left)
        shift
        left_tfplan=$1
        ;;
    --right)
        shift
        right_tfplan=$1
        ;;
    *)
        usage
        ;;
    esac
    shift # remove the current value for `$1` and use the next
done


if [[ -z ${left_tfplan} || -z ${right_tfplan} ]]; then
    echo -e "Not enough files provided to compare\n"
    usage
fi

echo "Comparing ${left_tfplan} to ${right_tfplan}..."


function plan_change() {
  terraform show -json $1 | jq -r '.resource_changes[] | select(.change.actions[] | contains("no-op") or contains("read") | not)' > "$1_filtered.json"
}

plan_change ${left_tfplan}
plan_change ${right_tfplan}

diff <(jq --sort-keys . ${left_tfplan}_filtered.json) <(jq --sort-keys . ${right_tfplan}_filtered.json)
