#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# Find all terraform folders and create/upgrade lock files.
# Run from root folder

find . -type d -name terraform -not -path "*/.cnab/*" -exec echo In Dir: {} \; -exec terraform -chdir={} init -upgrade=true -backend=false \;
