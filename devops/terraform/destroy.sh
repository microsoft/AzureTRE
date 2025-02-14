#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# shellcheck disable=SC1091
source ../scripts/mgmtstorage_add_network_exception.sh

terraform destroy -auto-approve