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
  if [[ "$tre_rg" == *-mgmt ]]; then
    echo "Management-only environment ${tre_rg} has no core services to stop. Keeping it until the destroy threshold."
    return 0
  fi
  local tre_id=${tre_rg#"rg-"}
  TRE_ID=${tre_id} devops/scripts/control_tre.sh stop
}

function destroyEnv ()
{
  # The destroy helper accepts the core name even when only management exists.
  devops/scripts/destroy_env_no_terraform.sh --core-tre-rg "${1%-mgmt}" --no-wait
}

# Check before any cleanup, including PR environments. Comment-triggered PR tests
# report the default branch, so a branch filter would miss the environment in use.
# Defer the entire sweep while another run is active, including queued runs.
function skip_cleanup_if_workflows_active ()
{
  local status active_runs
  for status in requested waiting pending queued in_progress; do
    if ! active_runs=$(gh api --paginate "repos/${GITHUB_REPOSITORY}/actions/runs?status=${status}&per_page=100" |
      jq --slurp --compact-output --exit-status --arg run_id "${GITHUB_RUN_ID}" '
        if length == 0 then error("No workflow data returned")
        elif any(.[]; type != "object") then error("Invalid workflow response page")
        elif any(.[]; (.workflow_runs | type) != "array") then
          error("Expected workflow_runs to be an array on every page")
        else [.[].workflow_runs[] | select((.id | tostring) != $run_id)]
        end'); then
      echo "Could not check active workflow runs. Stopping cleanup." >&2
      exit 1
    fi

    if [[ "${active_runs}" != "[]" ]]; then
      echo "Skipping environment cleanup while other workflow runs are ${status}:"
      echo "${active_runs}" | jq -r '.[].html_url'
      exit 0
    fi
  done
}

skip_cleanup_if_workflows_active

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

# Check again in case a workflow started during the environment cleanup.
skip_cleanup_if_workflows_active

# Delete workspace resource groups left behind by tests on main.
az group list --query "[?starts_with(name, 'rg-${MAIN_TRE_ID}-ws-')].name" -o tsv |
while read -r rg_name; do
  echo "Deleting resource group: ${rg_name}"
  az group delete --yes --no-wait --name "${rg_name}"
done
