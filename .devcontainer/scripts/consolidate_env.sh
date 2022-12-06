#!/bin/bash

set -o errexit
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# usage: consolidate_env.sh [workdir] [file]

WORKDIR=${1:-"automatic"}
FILE=${2:-"automatic"}

# done with processing args and can set this
set -o nounset

# declare the variable and export to the caller's context
STRIP_COMMENTS="... comments=\"\""
GET_LEAF_KEYS="... | select(. == \"*\") | {(path | .[-1]): .}"
UPCASE_KEYS="with_entries(.key |= upcase)"
FORMAT_TO_ENV_FILE="to_entries| map(.key + \"=\" +  .value)|.[]"

# Export as UPPERCASE keys env vars
# shellcheck disable=SC2046
export $(yq e "$STRIP_COMMENTS|$GET_LEAF_KEYS|$UPCASE_KEYS| $FORMAT_TO_ENV_FILE" config.yaml)

# shellcheck disable=SC2086
cat $WORKDIR/templates/core/private.env >> $FILE
