#!/bin/bash
set -e

# By default the docker.sock file is not associated with docker group on codespaces or macOS
# which causes a permission issue when docker is run without sudo.

if ! docker ps > /dev/null 2>&1; then
  echo "docker ps failed, setting docker.sock permissions"
  sudo chgrp docker /var/run/docker.sock
  sudo chmod g+rw /var/run/docker.sock
fi
