#!/bin/bash
set -euo pipefail

VERSION=${1:-"$(curl --silent https://api.github.com/repos/terraform-docs/terraform-docs/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')"}
INSTALL_DIR=${2:-"/usr/local/bin"}

curl --fail --silent --show-error --location \
  "https://github.com/terraform-docs/terraform-docs/releases/download/v${VERSION}/terraform-docs-v${VERSION}-linux-amd64.tar.gz" \
  -o /tmp/terraform-docs.tar.gz
tar -xzf /tmp/terraform-docs.tar.gz -C /tmp terraform-docs
mkdir -p "$INSTALL_DIR"
mv /tmp/terraform-docs "$INSTALL_DIR/terraform-docs"
rm -f /tmp/terraform-docs.tar.gz
