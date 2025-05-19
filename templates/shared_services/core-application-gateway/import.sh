#!/bin/bash

set -o errexit
set -o pipefail
set +o nounset

while [ "$1" != "" ]; do
    case $1 in
    --mgmt_resource_group_name)
        shift
        mgmt_resource_group_name=$1
        ;;
    --mgmt_storage_account_name)
        shift
        mgmt_storage_account_name=$1
        ;;
    --container_name)
        shift
        container_name=$1
        ;;
    --key)
        shift
        key=$1
        ;;


    --tre_id)
        shift
        tre_id=$1
        ;;
    --azure_subscription_id)
        shift
        azure_subscription_id=$1
        ;;
    *)
        echo "Unexpected argument: '$1'"
        usage
        ;;
    esac

    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi

    shift # remove the current value for `$1` and use the next
done

set -o nounset

core_resource_group_name="rg-${tre_id}"
application_gateway_name="agw-${tre_id}"

terraform -chdir=terraform init -input=false -backend=true -reconfigure \
  -backend-config="resource_group_name=${mgmt_resource_group_name}" \
  -backend-config="storage_account_name=${mgmt_storage_account_name}" \
  -backend-config="container_name=${container_name}" \
  -backend-config="key=${key}"

terraform -chdir=terraform import \
  -var "tre_id=${tre_id}" \
  azurerm_application_gateway.agw \
  "/subscriptions/${azure_subscription_id}/resourceGroups/${core_resource_group_name}/providers/Microsoft.Network/applicationGateways/${application_gateway_name}"