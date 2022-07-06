#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

core_rg_rid=$(terraform show -json | jq -r '.values.root_module.resources[] | select(.address=="azurerm_resource_group.core") | .values.id')
echo "Current tags:"
az tag list --resource-id "${core_rg_rid}"

version=$(cat "${script_dir}"/../version.txt)

# doesn't work with quotes
# shellcheck disable=SC2206
version_array=( ${version//=/ } ) # split by =
coded_version="${version_array[1]//\"}" # second element is what we want, remove " chars

git_origin="NA"
git_commit="NA"

if command -v git &> /dev/null; then
  git_origin=$(git config --get remote.origin.url)
  git_commit=$(git show --oneline -s)
fi

az tag update --operation merge --tags coded_version="${coded_version}" git_origin="${git_origin}" git_commit="${git_commit}" --resource-id "${core_rg_rid}"
echo "Updated tags:"
az tag list --resource-id "${core_rg_rid}"
