#!/bin/bash
set -e

script_dir=$(realpath $(dirname "${BASH_SOURCE[0]}"))
tf_dir=$(realpath "${script_dir}/../../templates/core/terraform")

export RESOURCE_GROUP=$(terraform -chdir=${tf_dir} output -raw core_resource_group_name)
export APPLICATION_GATEWAY=$(terraform -chdir=${tf_dir} output -raw app_gateway_name)
export STORAGE_ACCOUNT=$(terraform -chdir=${tf_dir} output -raw static_web_storage)
export KEYVAULT=$(terraform -chdir=${tf_dir} output -raw keyvault_name)
export FQDN=$(terraform -chdir=${tf_dir} output -raw azure_tre_fqdn)

echo "RESOURCE_GROUP=${RESOURCE_GROUP}"
echo "APPLICATION_GATEWAY=${APPLICATION_GATEWAY}"
echo "STORAGE_ACCOUNT=${STORAGE_ACCOUNT}"
echo "KEYVAULT=${KEYVAULT}"
echo "FQDN=${FQDN}"
