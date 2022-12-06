#!/bin/bash

set -o errexit
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# usage: consolidate_env.sh [workdir] [file]

WORKDIR=${1:-"automatic"}
FILE=${2:-"automatic"}

# done with processing args and can set this
set -o nounset

# # YQ query to strip comments
# STRIP_COMMENTS="... comments=\"\""
# # YQ query to get leaf keys
# GET_LEAF_KEYS="... | select(. == \"*\") | {(path | .[-1]): .}"
# # YQ query to uppercase keys
# UPCASE_KEYS="with_entries(.key |= upcase)"
# # YQ query to map yaml entries to the following format: key=value
# # needed for later env export
# FORMAT_TO_ENV_FILE="to_entries| map(.key + \"=\" +  .value)|.[]"

# # Export as UPPERCASE keys env vars
# # shellcheck disable=SC2046
# export $(yq e "$STRIP_COMMENTS|$GET_LEAF_KEYS|$UPCASE_KEYS| $FORMAT_TO_ENV_FILE" config.yaml)

# shellcheck disable=SC2086
cat $WORKDIR/templates/core/private.env >> $FILE
