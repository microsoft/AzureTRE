#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

workspace="${GITHUB_WORKSPACE:-$PWD}"
cd "$workspace"

case "${TARGET_KIND:-}" in
  docker)
    args=(buildx build --pull)
    for arg in ${BUILD_ARGS:-}; do
      args+=(--build-arg "$arg")
    done
    docker "${args[@]}" \
      --file "${DOCKERFILE:?Missing Dockerfile path}" "${CONTEXT:?Missing build context}"
    ;;
  porter)
    arg() { sed -n "s/^ARG $1=//p" .devcontainer/Dockerfile; }
    # Each attempt gets a new directory, including after a partial installation.
    PORTER_HOME="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/dockerfile-build-porter.XXXXXX")"
    trap 'rm -rf "$PORTER_HOME"' EXIT
    PORTER_VERSION="$(arg PORTER_VERSION)"
    PORTER_TERRAFORM_MIXIN_VERSION="$(arg PORTER_TERRAFORM_MIXIN_VERSION)"
    PORTER_AZ_MIXIN_VERSION="$(arg PORTER_AZ_MIXIN_VERSION)"
    PORTER_AZURE_PLUGIN_VERSION="$(arg PORTER_AZURE_PLUGIN_VERSION)"
    USERNAME="$(id -un)"
    export PORTER_HOME PORTER_VERSION PORTER_TERRAFORM_MIXIN_VERSION
    export PORTER_AZ_MIXIN_VERSION PORTER_AZURE_PLUGIN_VERSION USERNAME
    .devcontainer/scripts/porter-v1.sh
    export PATH="$PORTER_HOME:$PATH"
    cd "${BUNDLE_DIR:?Missing Porter bundle directory}"
    "${workspace}/devops/scripts/porter_build_bundle.sh"
    ;;
  *)
    echo "Unknown build target kind: ${TARGET_KIND:-missing}" >&2
    exit 2
    ;;
esac
