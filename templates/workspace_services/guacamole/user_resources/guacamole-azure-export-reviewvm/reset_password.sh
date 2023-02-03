#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

secret_name=$1
keyvault_name=$2
username=$3
resource_id=$4
password="$(LC_ALL=C tr -dc 'A-Za-z0-9_%@' </dev/urandom | head -c 16 ; echo)"

secret_value="$username
$password"

# Persist new password to keyvault
az keyvault secret set --name "$secret_name" --vault-name "$keyvault_name" --value "$secret_value"

# Set new VM password
az vm user update --ids "$resource_id" --username "$username" --password "$password"
