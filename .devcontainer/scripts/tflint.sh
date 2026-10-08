#!/bin/bash
set -euo pipefail

VERSION=${1:-"$(curl --silent https://api.github.com/repos/terraform-linters/tflint/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')"}
INSTALL_DIR=${2:-"/usr/local/bin"}

curl --fail --silent --show-error --location \
  "https://github.com/terraform-linters/tflint/releases/download/v${VERSION}/tflint_linux_amd64.zip" \
  -o /tmp/tflint.zip
unzip -q /tmp/tflint.zip -d /tmp
mkdir -p "$INSTALL_DIR"
mv /tmp/tflint "$INSTALL_DIR/tflint"
rm -f /tmp/tflint.zip
