#!/bin/bash
sudo tee /etc/pip.conf > /dev/null <<'EOF'
[global]
index = ${nexus_proxy_url}/repository/pypi/pypi
index-url = ${nexus_proxy_url}/repository/pypi/simple
trusted-host = ${nexus_proxy_url}
EOF
