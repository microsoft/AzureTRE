#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# shellcheck disable=SC1091
source ../scripts/storage_enable_public_access.sh

PLAN_FILE="devops.tfplan"

terraform init -input=false -backend=true -reconfigure
terraform plan -out ${PLAN_FILE}
terraform apply -auto-approve ${PLAN_FILE}

./update_tags.sh
