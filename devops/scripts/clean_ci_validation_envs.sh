#!/bin/bash

# This script cleans/deletes Azure environments created in CI.
# A resource group will be evaluated if its name starts with aspecific prefix
# and tagged with the 'ci_git_ref' tag.
# If the RG was created as part of a PR, then it will be deleted if the PR
# isn't open anymore. In all other cases (like regular branches), it will
# be deleted if the branch doesn't exist.

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

function deleteEnv ()
{
  local tre_rg="$1"
  locks=$(az group lock list -g $tre_rg --query [].id -o tsv)
  az resource lock delete --ids ${locks}
  az group delete --resource-group "${tre_rg}" --yes --no-wait
  # each mgmt is per tre so we should delete that too.
  az group delete --resource-group "${tre_rg}-mgmt" --yes --no-wait
}

echo "Refs:"
git show-ref

open_prs=$(gh pr list --state open --json number,title)

# Resource groups that start with a specific string and have the ci_git_ref tag whose value starts with "ref"
az group list --query "[?starts_with(name, 'rg-tre') && tags.ci_git_ref != null && starts_with(tags.ci_git_ref, 'refs')].[name, tags.ci_git_ref]" -o tsv |
while read -r rg_name rg_ref_name; do
  if [[ ${rg_ref_name} == refs\/pull* ]]
  then
    # this rg originated from an external PR (i.e. a fork)
    pr_num=${rg_ref_name//[!0-9]/}
    if [ $(echo ${open_prs} | jq -c "[ .[] | select( .number | contains(${pr_num})) ] | length") == 0 ]
    then
      echo "PR ${pr_num} (derived from ref ${rg_ref_name}) is not open, and environment ${rg_name} can be deleted."
      deleteEnv ${rg_name}
    fi
  else
    # this rg originated from an internal branch on this repo
    ref_in_remote="${rg_ref_name/heads/remotes\/origin}"
    if ! $(git show-ref -q $ref_in_remote)
    then
      echo "Ref ${rg_ref_name} does not exists, and environment ${rg_name} can be deleted."
      deleteEnv ${rg_name}
    fi
  fi
done
