#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: MIT

set -eo pipefail

run_as_root() {
  if (( EUID == 0 )); then
    "$@"
  elif command -v sudo >/dev/null; then
    sudo "$@"
  else
    echo "root privileges are required to update docker socket permissions" >&2
    return 1
  fi
}

main() {
  local target_user="${1:-${SUDO_USER:-${USER:-vscode}}}"
  local socket_path="/var/run/docker.sock"
  local socket_gid
  local docker_gid
  local target_group="docker"
  local existing_group_name=""

  # Match the container-side group to the mounted socket instead of trying
  # to rewrite bind-mounted socket metadata from inside the container.
  if [[ ! -S "${socket_path}" ]]; then
    echo "docker socket not found at ${socket_path}; skipping permission fix"
    return 0
  fi

  socket_gid="$(stat -c '%g' "${socket_path}")"

  if getent group "${socket_gid}" >/dev/null; then
    existing_group_name="$(getent group "${socket_gid}" | cut -d: -f1)"
  fi

  if getent group docker >/dev/null; then
    docker_gid="$(getent group docker | cut -d: -f3)"

    if [[ "${docker_gid}" != "${socket_gid}" ]]; then
      if [[ -n "${existing_group_name}" ]]; then
        target_group="${existing_group_name}"
        echo "docker group GID ${docker_gid} does not match socket GID ${socket_gid}; using group ${target_group}"
      else
        echo "Updating docker group GID from ${docker_gid} to ${socket_gid}"
        run_as_root groupmod -g "${socket_gid}" docker
      fi
    fi
  else
    if [[ -n "${existing_group_name}" ]]; then
      target_group="${existing_group_name}"
      echo "Using existing group ${target_group} for docker socket GID ${socket_gid}"
    else
      echo "Creating docker group with GID ${socket_gid}"
      run_as_root groupadd -g "${socket_gid}" docker
    fi
  fi

  run_as_root usermod -aG "${target_group}" "${target_user}"
  run_as_root chmod g+rw "${socket_path}"
}

main "$@"
