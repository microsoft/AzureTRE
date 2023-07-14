#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# Get Docker Public key from Nexus
curl -fsSL "${NEXUS_PROXY_URL}"/repository/docker-public-key/gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/docker-archive-keyring.gpg

# Get Microsoft Public key from Nexus
curl -fsSL "${NEXUS_PROXY_URL}"/repository/microsoft-keys/microsoft.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/microsoft.gpg
