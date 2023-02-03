#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mgmt_rg_rid=$(terraform show -json | jq -r '.values.root_module.resources[] | select(.address=="azurerm_resource_group.mgmt") | .values.id')
echo "Current tags:"
az tag list --resource-id "${mgmt_rg_rid}"

version=$(cat "${script_dir}"/../version.txt)

# doesn't work with quotes
# shellcheck disable=SC2206
version_array=( ${version//=/ } ) # split by =
coded_version="${version_array[1]//\"}" # second element is what we want, remove " chars

git_origin="NA"
git_commit="NA"

is_inside_git_repo() {
    git --git-dir="${1}" rev-parse --is-inside-work-tree >/dev/null 2>&1 && echo "true"
}

if command -v git &> /dev/null; then

  git_dir="${PWD}/.git"
  if [ "$(is_inside_git_repo "${git_dir}")" != "true" ]; then
    git_dir="${OLDPWD}/.git"
    if [ "$(is_inside_git_repo "${git_dir}")" != "true" ]; then
      echo "Couldn't find git directory."
      git_dir=""
    fi
  fi

  if [ -n "${git_dir}" ]; then
    git_origin=$(git --git-dir="${git_dir}" config --get remote.origin.url)
    git_commit=$(git --git-dir="${git_dir}" show --oneline -s)
  fi

fi


az tag update --operation merge --tags coded_version="${coded_version}" git_origin="${git_origin}" git_commit="${git_commit}" --resource-id "${mgmt_rg_rid}"
echo "Updated tags:"
az tag list --resource-id "${mgmt_rg_rid}"
