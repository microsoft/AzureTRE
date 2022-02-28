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
  if [[ ! -z ${TRE_ID:-} ]]; then
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

locks=$(az group lock list -g ${core_tre_rg} --query [].id -o tsv)
if [ ! -z "${locks:-}" ]
then
  echo "Deleting locks..."
  az resource lock delete --ids ${locks}
fi

delete_resource_diagnostic() {
  # the command will return an error if the resource doesn't support this setting, so need to suppress it.
  az monitor diagnostic-settings list --resource $1 --query "value[].name" -o tsv 2> /dev/null |
  while read -r diag_name; do
    echo "Deleting ${diag_name} on $1"
    az monitor diagnostic-settings delete --resource $1 --name ${diag_name}
  done
}
export -f delete_resource_diagnostic

echo "Looking for diagnostic settings..."
# sometimes, diagnostic settings aren't deleted with the resource group. we need to manually do that,
# and unfortuanlly, there's no easy way to list all that are present.
# using xargs to run in parallel.
az resource list --resource-group ${core_tre_rg} --query '[].[id]' -o tsv | xargs -P 10 -I {} bash -c 'delete_resource_diagnostic "{}"'

# purge keyvault if possible (makes it possible to reuse the same tre_id later)
# this has to be done before we delete the resource group since we don't wait for it to complete
if [[ $(az keyvault list --resource-group ${core_tre_rg} --query '[?proterties.enablePurgeProtection==null] | length (@)') != 0 ]]; then
  tre_id=${core_tre_rg#"rg-"}
  keyvault_name="kv-${tre_id}"

  echo "Deleting keyvault: ${keyvault_name}"
  az keyvault delete --name ${keyvault_name} --resource-group ${core_tre_rg}

  echo "Purging keyvault: ${keyvault_name}"
  az keyvault purge --name ${keyvault_name} ${no_wait_option}
fi

# this will find the mgmt, core resource groups as well as any workspace ones
az group list --query "[?starts_with(name, '${core_tre_rg}')].[name]" -o tsv |
while read -r rg_item; do
  echo "Deleting resource group: ${rg_item}"
  az group delete --resource-group "${rg_item}" --yes ${no_wait_option}
done
