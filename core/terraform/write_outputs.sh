#!/bin/bash
set -o errexit
set -o nounset
set -o pipefail

output_file=${1:?Usage: write_outputs.sh OUTPUT_FILE}
output_temporary=$(mktemp "${output_file}.tmp.XXXXXX")
trap 'rm -f "$output_temporary"' EXIT

# Keep the previous cache until Terraform and the environment converter succeed.
terraform output -json > "$output_temporary"
"$(dirname "$0")/json-to-env.sh" < "$output_temporary" > /dev/null
mv "$output_temporary" "$output_file"
