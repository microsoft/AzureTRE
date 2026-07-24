#!/bin/bash
set -euo pipefail

get_latest_release() {
  curl --silent "https://api.github.com/repos/$1/releases/latest" |
  grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/'
}

VERSION=${1:-"$(get_latest_release terraform-docs/terraform-docs)"}
INSTALL_DIR=${2:-"/usr/local/bin"}
CMD=terraform-docs
NAME=terraform-docs

echo -e "\e[34m»»» 📦 \e[32mInstalling \e[33m$NAME v$VERSION\e[0m ..."

curl -sSL "https://github.com/terraform-docs/terraform-docs/releases/download/v${VERSION}/terraform-docs-v${VERSION}-linux-amd64.tar.gz" -o /tmp/tfdocs.tar.gz
tar -xzf /tmp/tfdocs.tar.gz -C /tmp > /dev/null
mkdir -p "$INSTALL_DIR"
mv /tmp/terraform-docs "$INSTALL_DIR"
rm -f /tmp/tfdocs.tar.gz

echo -e "\n\e[34m»»» 💾 \e[32mInstalled to: \e[33m$(which $CMD)"
echo -e "\e[34m»»» 💡 \e[32mVersion details: \e[39m$($CMD --version)"
