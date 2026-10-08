#!/bin/bash
# Prints the build matrix for the "Dockerfile Build Check" workflow as a JSON
# array. Each entry is one build target:
#
#   name        Label shown in the GitHub Actions UI
#   safe_name   The label with "/" replaced and a leading dot removed
#   kind        "docker" for a plain Dockerfile, "porter" for a bundle
#   dockerfile  The Dockerfile path (kind: docker)
#   context     The build context path (kind: docker)
#   build_args  Extra "--build-arg" values, space separated (kind: docker)
#   dir         The bundle directory (kind: porter)
#
# On a pull request the caller passes the list of changed files, and the
# script keeps only the targets that those files affect. Any other event, or a
# change to the workflow itself, selects every target.
#
# Environment:
#   EVENT_NAME        GitHub event name, for example "pull_request"
#   WORKFLOW_CHANGED  "true" when the workflow file changed
#   CHANGED_FILES     JSON array of changed build-input paths (pull requests only)
#   GITHUB_OUTPUT     When set, the script also writes "matrix=<json>" there
set -o errexit
set -o pipefail
set -o nounset

EVENT_NAME="${EVENT_NAME:-}"
WORKFLOW_CHANGED="${WORKFLOW_CHANGED:-false}"
CHANGED_FILES="${CHANGED_FILES:-[]}"

# Keep paths intact, including spaces, without evaluating shell quoting.
jq -e 'type == "array" and all(.[]; type == "string")' <<< "$CHANGED_FILES" >/dev/null
changed_files=()
while IFS= read -r -d '' file; do
  changed_files+=("$file")
done < <(jq -j '.[] | ., "\u0000"' <<< "$CHANGED_FILES")

tracked_files="$(git ls-files)"

# A plain Dockerfile needs an explicit build context, so list each one here.
# Format: dockerfile|context|build_args
plain_targets=(
  ".devcontainer/Dockerfile|.|INTERACTIVE=true"
  "airlock_processor/Dockerfile|airlock_processor|"
  "api_app/Dockerfile|api_app|"
  "resource_processor/vmss_porter/Dockerfile|resource_processor|"
  "templates/shared_services/gitea/docker/Dockerfile|templates/shared_services/gitea/docker|"
  "templates/workspace_services/gitea/docker/Dockerfile|templates/workspace_services/gitea/docker|"
  "templates/workspace_services/guacamole/e2e-tests/playwright/Dockerfile|templates/workspace_services/guacamole/e2e-tests/playwright|"
  "templates/workspace_services/guacamole/guacamole-server/docker/Dockerfile|templates/workspace_services/guacamole/guacamole-server|"
)

# Consumer and source directories declared in porter-build-context.env files.
# Tests check these dependencies and the workflow filters against those files.
named_contexts=(
  "templates/workspaces/airlock-import-review|templates/workspaces/base"
  "templates/workspaces/unrestricted|templates/workspaces/base"
  "templates/workspace_services/guacamole/user_resources/guacamole-azure-import-reviewvm|templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm"
  "templates/workspace_services/guacamole/user_resources/guacamole-azure-export-reviewvm|templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm"
  "templates/workspace_services/guacamole/user_resources/guacamole-azure-export-reviewvm|templates/workspace_services/guacamole/user_resources/guacamole-azure-import-reviewvm"
)

# Fail when a tracked plain Dockerfile exists that the list above does not
# know, so a new Dockerfile cannot slip past the check. git ls-files skips
# ignored and untracked paths such as node_modules, .cnab and worktrees.
while IFS= read -r found; do
  known=false
  for entry in "${plain_targets[@]}"; do
    if [ "${entry%%|*}" = "$found" ]; then
      known=true
      break
    fi
  done
  if [ "$known" = false ]; then
    echo "::error::${found} is not listed in $0. Add it with its build context." >&2
    exit 1
  fi
done < <(printf '%s\n' "$tracked_files" | grep -E '(^|/)Dockerfile$' | sort)

# Check tracked pairs before selection so an incomplete bundle cannot disappear
# from the matrix. Removing both files still removes the bundle cleanly.
while IFS= read -r bundle_file; do
  dir="$(dirname "$bundle_file")"
  if [ "${bundle_file##*/}" = "porter.yaml" ]; then
    required="${dir}/Dockerfile.tmpl"
  else
    required="${dir}/porter.yaml"
  fi
  if ! grep -Fxq "$required" <<< "$tracked_files"; then
    echo "::error::Incomplete Porter bundle: ${dir}. Track ${required} or remove both bundle files." >&2
    exit 1
  fi
done < <(printf '%s\n' "$tracked_files" | grep -E '^templates/.*/(porter\.yaml|Dockerfile\.tmpl)$' | sort)

select_all=true
if [ "$EVENT_NAME" = "pull_request" ] && [ "$WORKFLOW_CHANGED" != "true" ]; then
  select_all=false
fi

# Shared Porter tools affect every bundle. Named contexts also select consumers.
is_selected() {
  local dir="$1"
  local dockerfile="$2"
  local kind="$3"
  if [ "$select_all" = true ]; then
    return 0
  fi
  local file dependency consumer source
  for file in "${changed_files[@]}"; do
    if [ "$file" = "$dockerfile" ] || [ "$file" = "${dir}/porter.yaml" ]; then
      return 0
    fi
    if [ "$kind" = "porter" ]; then
      case "$file" in
        .devcontainer/Dockerfile|.devcontainer/scripts/porter-v1.sh|devops/scripts/porter_build_bundle.sh)
          return 0
          ;;
      esac
      if [ "$file" = "${dir}/porter-build-context.env" ]; then
        return 0
      fi
      for dependency in "${named_contexts[@]}"; do
        IFS='|' read -r consumer source <<< "$dependency"
        if [[ "$file" == "$source/"* ]] && { [ "$dir" = "$source" ] || [ "$dir" = "$consumer" ]; }; then
          return 0
        fi
      done
    fi
    if [ "$dir" = ".devcontainer" ] && [[ "$file" == .devcontainer/* ]]; then
      return 0
    fi
  done
  return 1
}

label() {
  # Drop the "templates/" prefix to keep job names short.
  echo "${1#templates/}"
}

targets=()

for entry in "${plain_targets[@]}"; do
  IFS='|' read -r dockerfile context build_args <<< "$entry"
  # A removed Dockerfile is no longer a build target.
  if ! grep -Fxq "$dockerfile" <<< "$tracked_files"; then
    continue
  fi
  dir="$(dirname "$dockerfile")"
  if is_selected "$dir" "$dockerfile" docker; then
    name="$(label "$dir")"
    safe_name="${name//\//_}"
    targets+=("$(jq -c -n \
      --arg name "$name" \
      --arg safe_name "${safe_name#.}" \
      --arg dockerfile "$dockerfile" \
      --arg context "$context" \
      --arg build_args "$build_args" \
      '{name: $name, safe_name: $safe_name, kind: "docker", dockerfile: $dockerfile, context: $context, build_args: $build_args}')")
  fi
done

while IFS= read -r dockerfile; do
  dir="$(dirname "$dockerfile")"
  if is_selected "$dir" "$dockerfile" porter; then
    name="$(label "$dir")"
    safe_name="${name//\//_}"
    targets+=("$(jq -c -n \
      --arg name "$name" \
      --arg safe_name "${safe_name#.}" \
      --arg dir "$dir" \
      '{name: $name, safe_name: $safe_name, kind: "porter", dir: $dir}')")
  fi
done < <(printf '%s\n' "$tracked_files" | grep -E '^templates/.*/Dockerfile\.tmpl$' | sort)

matrix="$(printf '%s\n' "${targets[@]}" | jq -c -s '.')"
if [ "${#targets[@]}" -eq 0 ]; then
  matrix="[]"
fi

echo "Selected ${#targets[@]} build targets:"
echo "$matrix" | jq -r '.[] | "  \(.kind)\t\(.name)"'

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "matrix=${matrix}" >> "$GITHUB_OUTPUT"
fi
