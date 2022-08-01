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

function stopEnv ()
{
  local tre_rg="$1"
  local tre_id=${tre_rg#"rg-"}
  TRE_ID=${tre_id} devops/scripts/control_tre.sh stop
}

az config set extension.use_dynamic_install=yes_without_prompt

echo "Refs:"
git show-ref

open_prs=$(gh pr list --state open --json number,title,headRefName,updatedAt)

# Resource groups that start with a specific string and have the ci_git_ref tag whose value starts with "ref"
az group list --query "[?starts_with(name, 'rg-tre') && tags.ci_git_ref != null && starts_with(tags.ci_git_ref, 'refs')].[name, tags.ci_git_ref]" -o tsv |
while read -r rg_name rg_ref_name; do
  if [[ "${rg_ref_name}" == refs/pull* ]]
  then
    # this rg originated from an external PR (i.e. a fork)
    pr_num=${rg_ref_name//[!0-9]/}
    is_open_pr=$(echo "${open_prs}" | jq -c "[ .[] | select( .number | contains(${pr_num})) ] | length")
    if [ "${is_open_pr}" == "0" ]
    then
      echo "PR ${pr_num} (derived from ref ${rg_ref_name}) is not open. Environment in ${rg_name} will be deleted."
      devops/scripts/destroy_env_no_terraform.sh --core-tre-rg "${rg_name}" --no-wait
      continue
    fi

    # The pr is still open...
    # The ci_git_ref might not contain the actual ref, but the "pull" ref. We need the actual head branch name.
    head_ref=$(echo "${open_prs}" | jq -r ".[] | select (.number == ${pr_num}) | .headRefName")

    # Checking when was the last commit on the branch.
    last_commit_date_string=$(git for-each-ref --sort='-committerdate:iso8601' --format=' %(committerdate:iso8601)%09%(refname)' "refs/remotes/origin/${head_ref}" | cut -f1)

    # updatedAt is changed on commits but probably comments as well.
    # For PRs from forks we'll need this as the repo doesn't have the PR code handy.
    pr_updated_at=$(echo "${open_prs}" | jq -r ".[] | select (.number == ${pr_num}) | .updatedAt")

    echo "PR ${pr_num} source branch is ${head_ref}, last commit was on: ${last_commit_date_string}, last update was on: ${pr_updated_at}"

    if [ -n "${last_commit_date_string}" ]; then
      diff_in_hours=$(( ($(date +%s) - $(date -d "${last_commit_date_string}" +%s) )/(60*60) ))
    else
      diff_in_hours=$(( ($(date +%s) - $(date -d "${pr_updated_at}" +%s) )/(60*60) ))
    fi

    if (( diff_in_hours > BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_DESTROY )); then
      echo "No recent activity on ${head_ref}. Environment in ${rg_name} will be destroyed."
      devops/scripts/destroy_env_no_terraform.sh --core-tre-rg "${rg_name}" --no-wait
    elif (( diff_in_hours > BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_STOP )); then
      echo "No recent activity on ${head_ref}. Environment in ${rg_name} will be stopped."
      stopEnv "${rg_name}"
    fi
  else
    # this rg originated from an internal branch on this repo
    ref_in_remote="${rg_ref_name/heads/remotes\/origin}"
    if ! git show-ref -q "$ref_in_remote"
    then
      echo "Ref ${rg_ref_name} does not exist, and environment ${rg_name} can be deleted."
      devops/scripts/destroy_env_no_terraform.sh --core-tre-rg "${rg_name}" --no-wait
    else
       # checking when was the last commit on the branch.
      last_commit_date_string=$(git for-each-ref --sort='-committerdate:iso8601' --format=' %(committerdate:iso8601)%09%(refname)' "${ref_in_remote}" | cut -f1)
      echo "Native ref is ${rg_ref_name}, last commit was on: ${last_commit_date_string}"
      diff_in_hours=$(( ($(date +%s) - $(date -d "${last_commit_date_string}" +%s) )/(60*60) ))

      if (( diff_in_hours > BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_DESTROY )); then
        echo "No recent activity on ${rg_ref_name}. Environment in ${rg_name} will be destroyed."
        devops/scripts/destroy_env_no_terraform.sh --core-tre-rg "${rg_name}" --no-wait
      elif (( diff_in_hours > BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_STOP )); then
        echo "No recent activity on ${rg_ref_name}. Environment in ${rg_name} will be stopped."
        stopEnv "${rg_name}"
      fi
    fi
  fi
done

# check if any workflows run on the main branch (except the cleanup=current one)
# to prevent us deleting a workspace for which an E2E (on main) is currently running
if [[ -z $(gh api "https://api.github.com/repos/microsoft/AzureTRE/actions/runs?branch=main&status=in_progress" | jq --arg name "$GITHUB_WORKFLOW" '.workflow_runs | select(.[].name != $name)') ]]
then
  # if not, we can delete old workspace resource groups that were left due to errors.
  az group list --query "[?starts_with(name, 'rg-${MAIN_TRE_ID}-ws-')].name" -o tsv |
  while read -r rg_name; do
    echo "Deleting resource group: ${rg_name}"
    az group delete --yes --no-wait --name "${rg_name}"
  done
else
  echo "Workflows are running on the main branch, can't delete e2e workspaces."
fi
