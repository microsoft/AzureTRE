#!/bin/bash

# This script deletes a specific deployment of TRE including resource
# groups of the managment (ops) part, core as well as all workspace ones.
# It's doing this by finding all resource groups that start with the same
# name as the core one!
# If possible it will purge the keyvault making it possible to reuse the same
# TRE_ID for a later deployment.

set -o errexit
set -o pipefail
# set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 --core-tre-rg "something" [--no-wait]

    Options:
        --core-tre-rg   The core resource group name of the TRE.
        --no-wait       Doesn't wait for delete operations to complete and exits asap.
USAGE
    exit 1
}

no_wait=false

while [ "$1" != "" ]; do
    case $1 in
    --core-tre-rg)
        shift
        core_tre_rg=$1
        ;;
    --no-wait)
        no_wait=true
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

# done with processing args and can set this
set -o nounset

if [[ -z ${core_tre_rg:-} ]]; then
  if [[ -n ${TRE_ID:-} ]]; then
    core_tre_rg="rg-${TRE_ID}"
  else
    echo "Core TRE resource group name wasn't provided"
    usage
  fi
fi

no_wait_option=""
if ${no_wait}
then
  no_wait_option="--no-wait"
fi

script_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

# shellcheck disable=SC1091
source "$script_dir/kv_add_network_exception.sh"

group_show_result=$(az group show --name "${core_tre_rg}" > /dev/null 2>&1; echo $?)
if [[ "$group_show_result" !=  "0" ]]; then
  echo "Resource group ${core_tre_rg} not found - skipping destroy"
  exit 0
fi

locks=$(az group lock list -g "${core_tre_rg}" --query [].id -o tsv | tr -d \')
if [ -n "${locks:-}" ]
then
  for lock in $locks
  do
    echo "Deleting lock ${lock}..."
    az resource lock delete --ids "${lock}"
  done
fi

delete_resource_diagnostic() {
  # the command will return an error if the resource doesn't support this setting, so need to suppress it.
  # first line works on azcli 2.37, second line works on azcli 2.42
  { az monitor diagnostic-settings list --resource "$1" --query "value[].name" -o tsv 2> /dev/null \
    && az monitor diagnostic-settings list --resource "$1" --query "[].name" -o tsv 2> /dev/null ; } |
  while read -r diag_name; do
    echo "Deleting ${diag_name} on $1"
    az monitor diagnostic-settings delete --resource "$1" --name "${diag_name}"
  done
}
export -f delete_resource_diagnostic

echo "Looking for diagnostic settings..."
# sometimes, diagnostic settings aren't deleted with the resource group. we need to manually do that,
# and unfortunately, there's no easy way to list all that are present.
# using xargs to run in parallel.
az resource list --resource-group "${core_tre_rg}" --query '[].[id]' -o tsv | xargs -P 10 -I {} bash -c 'delete_resource_diagnostic "{}"'
tre_id=${core_tre_rg#"rg-"}

# purge keyvault if possible (makes it possible to reuse the same tre_id later)
# this has to be done before we delete the resource group since we might not wait for it to complete
keyvault_name="kv-${tre_id}"
keyvault=$(az keyvault show --name "${keyvault_name}" --resource-group "${core_tre_rg}" -o json || echo 0)
if [ "${keyvault}" != "0" ]; then
  secrets=$(az keyvault secret list --vault-name "${keyvault_name}" -o json | jq -r '.[].id')
  for secret_id in ${secrets}; do
    echo "Deleting ${secret_id}"
    az keyvault secret delete --id "${secret_id}"
  done

  keys=$(az keyvault key list --vault-name "${keyvault_name}" -o json | jq -r '.[].id')
  for key_id in ${keys}; do
    echo "Deleting ${key_id}"
    az keyvault key delete --id "${key_id}"
  done

  certificates=$(az keyvault certificate list --vault-name "${keyvault_name}" -o json | jq -r '.[].id')
  for certificate_id in ${certificates}; do
    echo "Deleting ${certificate_id}"
    az keyvault certificate delete --id "${certificate_id}"
  done

  echo "Removing access policies so if the vault is recovered there are not there"
  access_policies=$(echo "$keyvault" | jq -r '.properties.accessPolicies[].objectId' )
  for access_policy_id in ${access_policies}; do
    echo "Attempting to delete access policy ${access_policy_id}"
    az keyvault delete-policy --name "${keyvault_name}" --resource-group "${core_tre_rg}" --object-id "${access_policy_id}" || echo "Not deleting access policy for ${access_policy_id}."
  done

fi

# Delete the vault if purge protection is not on.
if [[ $(az keyvault list --resource-group "${core_tre_rg}" --query "[?properties.enablePurgeProtection==``null``] | length (@)" -o tsv) != 0 ]]; then
  echo "Deleting keyvault: ${keyvault_name}"
  az keyvault delete --name "${keyvault_name}" --resource-group "${core_tre_rg}"

  echo "Purging keyvault: ${keyvault_name}"
  az keyvault purge --name "${keyvault_name}" ${no_wait_option}
else
  echo "Resource group ${core_tre_rg} doesn't have a keyvault without purge protection."
fi

# linked storage accounts don't get deleted with the workspace
workspace_name="log-${tre_id}"
workspace=$(az monitor log-analytics workspace show --workspace-name "${workspace_name}" --resource-group "${core_tre_rg}" || echo 0)
if [ "${workspace}" != "0" ]; then
  echo "Deleting Linked Storage accounts if present..."
  az monitor log-analytics workspace linked-storage list -g "${core_tre_rg}" --workspace-name "${workspace_name}" -o tsv --query '[].id' \
  | xargs -P 10 -I {} az rest --method delete --uri "{}?api-version=2020-08-01"
fi

# delete container repositories individually otherwise defender doesn't purge image scans
function purge_container_repositories() {
  local rg=$1

  local acrs
  acrs=$(az acr list --resource-group "$rg" --query [].name --output tsv)

  local acr
  for acr in $acrs; do
    echo "Found container registry ${acr}, deleting repositories..."

    local repositories
    repositories=$(az acr repository list --name "$acr" --output tsv)

    local repository
    for repository in $repositories; do
        echo "  Deleting: $repository"
        az acr repository delete --name "$acr" --repository "$repository" --yes --output none
    done
  done
}

# this will find the mgmt, core resource groups as well as any workspace ones
# we are reverse-sorting to first delete the workspace groups (might not be
# good enough because we use no-wait sometimes)
az group list --query "[?starts_with(name, '${core_tre_rg}')].[name]" -o tsv | sort -r |
while read -r rg_item; do
  purge_container_repositories "$rg_item"

  echo "Deleting resource group: ${rg_item}"
  # remove any resource locks on resources inside the resource group
  az lock list --resource-group "${rg_item}" --query "[].id" -o tsv | xargs -r -I {} az lock delete --id "{}"
  az group delete --resource-group "${rg_item}" --yes ${no_wait_option}
done
