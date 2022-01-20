#!/bin/bash
set -e

if [ -z "$DOCKER_GROUP_ID" ]; then
    groupadd g docker
else
    groupadd -g $DOCKER_GROUP_ID docker
fi

usermod -aG docker $1 && newgrp docker
getent group docker
