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
  python3 devops/scripts/ci_cleanup_scope.py verify-target --group "$1"
  local tre_rg="$1"
  if [[ "$tre_rg" == *-mgmt ]]; then
    echo "Management-only environment ${tre_rg} has no core services to stop. Keeping it until the destroy threshold."
    return 0
  fi
  local tre_id=${tre_rg#"rg-"}
  TRE_ID=${tre_id} devops/scripts/control_tre.sh stop
}

function destroyEnv ()
{
  python3 devops/scripts/ci_cleanup_scope.py verify-target --group "$1"
  # The destroy helper accepts the core name even when only management exists.
  devops/scripts/destroy_env_no_terraform.sh --core-tre-rg "${1%-mgmt}"
}

# Every mutating invocation must own the same reference group as deployment.
# The planner only reads inventory; matrix jobs select and recheck targets after
# acquiring their lock. Refuse legacy unscoped invocations.
python3 devops/scripts/ci_cleanup_scope.py verify-lock

if [[ "${CI_CLEANUP_REF}" == refs/heads/main ]]; then
  # The TRE_ID secret can be absent for cleanup. The previous sweep then matched nothing.
  if [[ -z "${MAIN_TRE_ID:-}" ]]; then
    echo "MAIN_TRE_ID is not set. Skipping main workspace cleanup."
    exit 0
  fi
  [[ "${MAIN_TRE_ID}" =~ ^[a-zA-Z0-9-]+$ ]] || { echo "Invalid main TRE ID" >&2; exit 1; }
  az group list --query "[?starts_with(name, 'rg-${MAIN_TRE_ID}-ws-')].name" -o tsv |
  while read -r rg_name; do
    [[ -n "$rg_name" ]] || continue
    echo "Deleting resource group: ${rg_name}"
    az group delete --yes --name "${rg_name}"
  done
  exit 0
fi

az config set extension.use_dynamic_install=yes_without_prompt

echo "Refs:"
git show-ref

open_prs=$(gh api --paginate "repos/${GITHUB_REPOSITORY}/pulls?state=open&per_page=100" |
  jq --slurp --compact-output --exit-status '
    if length == 0 or any(.[]; type != "array") then error("Invalid pull request pages")
    elif any(.[][]; (.number | type) != "number" or (.head.ref | type) != "string" or (.updated_at | type) != "string") then
      error("Invalid pull request details")
    else [.[][] | {number, headRefName: .head.ref, updatedAt: .updated_at}]
    end')

# Take a snapshot before deletion. A paired management group is handled through its
# core group, even if the core group disappears during this sweep. Untagged groups
# are never independent cleanup targets, including legacy management orphans.
resource_groups=$(az group list --query "[?starts_with(name, 'rg-tre')].{name:name, ci_git_ref:tags.ci_git_ref}" -o json)
cleanup_groups=$(jq -rs '
  if length != 1 then error("Expected one resource group list") else .[0] end |
  if type != "array" then error("Invalid resource group list")
  elif any(.[]; (.name | type) != "string" or (.ci_git_ref != null and (.ci_git_ref | type) != "string")) then
    error("Invalid resource group details")
  else . as $groups | .[]
    | select((.ci_git_ref // "") | test("^refs/(pull/[0-9]+/merge|heads/.+)$"))
    | .name as $name
    | select(($name | endswith("-mgmt") | not) or
        ($groups | any(.name == ($name | rtrimstr("-mgmt"))) | not))
    | [.name, .ci_git_ref] | @tsv
  end' <<< "$resource_groups")

echo "$cleanup_groups" |
while read -r rg_name rg_ref_name; do
  [[ -n "$rg_name" ]] || continue
  [[ "$rg_ref_name" == "$CI_CLEANUP_REF" ]] || continue
  if [[ "${rg_ref_name}" == refs/pull* ]]
  then
    # this rg originated from an external PR (i.e. a fork)
    pr_num=${rg_ref_name//[!0-9]/}
    is_open_pr=$(echo "${open_prs}" | jq -c "[ .[] | select( .number | contains(${pr_num})) ] | length")
    if [ "${is_open_pr}" == "0" ]
    then
      echo "PR ${pr_num} (derived from ref ${rg_ref_name}) is not open. Environment in ${rg_name} will be deleted."
      destroyEnv "${rg_name}"
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
      destroyEnv "${rg_name}"
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
      destroyEnv "${rg_name}"
    else
       # checking when was the last commit on the branch.
      last_commit_date_string=$(git for-each-ref --sort='-committerdate:iso8601' --format=' %(committerdate:iso8601)%09%(refname)' "${ref_in_remote}" | cut -f1)
      echo "Native ref is ${rg_ref_name}, last commit was on: ${last_commit_date_string}"
      diff_in_hours=$(( ($(date +%s) - $(date -d "${last_commit_date_string}" +%s) )/(60*60) ))

      if (( diff_in_hours > BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_DESTROY )); then
        echo "No recent activity on ${rg_ref_name}. Environment in ${rg_name} will be destroyed."
        destroyEnv "${rg_name}"
      elif (( diff_in_hours > BRANCH_LAST_ACTIVITY_IN_HOURS_FOR_STOP )); then
        echo "No recent activity on ${rg_ref_name}. Environment in ${rg_name} will be stopped."
        stopEnv "${rg_name}"
      fi
    fi
  fi
done
