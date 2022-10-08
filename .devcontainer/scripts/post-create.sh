#!/bin/bash
set -e

# docker socket fixup
sudo bash ./devops/scripts/set_docker_sock_permission.sh

# install tre CLI
(cd /workspaces/AzureTRE/cli/ && make install-cli)  && echo -e "\n# Set up tre completion\nsource <(_TRE_COMPLETE=bash_source tre)" >> ~/.bashrc

