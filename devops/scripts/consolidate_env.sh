#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# usage: consolidate_env.sh [workdir] [file]

WORKDIR=${1:-"automatic"}
FILE=${2:-"automatic"}

if [ -z "${USE_ENV_VARS_NOT_FILES:-}" ]; then
  # YQ query to get leaf keys
  GET_LEAF_KEYS=".. | select(. == \"*\") | {(path | .[-1]): .} "
  # YQ query to uppercase keys
  UPCASE_KEYS="with_entries(.key |= upcase)"
  # YQ query to map yaml entries to the following format: key=value
  # needed for later env export
  FORMAT_TO_ENV_FILE="to_entries| map(.key + \"=\" +  .value)|.[]"

  # Export as UPPERCASE keys to file
  yq e "$GET_LEAF_KEYS|$UPCASE_KEYS| $FORMAT_TO_ENV_FILE" config.yaml > "$FILE"

  if [ -f "$WORKDIR/core/private.env" ]; then
    cat "$WORKDIR/core/private.env" >> "$FILE"
  fi
fi
