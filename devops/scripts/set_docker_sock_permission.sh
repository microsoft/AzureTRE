#!/bin/bash
set -e

# By default the docker.sock file is not associated with docker group on codespaces or macOS
# which causes a permission issue when docker is run without sudo.

sudo chgrp docker /var/run/docker.sock
sudo chmod g+rw /var/run/docker.sock
