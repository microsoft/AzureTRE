#!/bin/bash
set -e

get_latest_release() {
  curl --silent "https://api.github.com/repos/$1/releases/latest" |
  grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/'
}

VERSION=${1:-"$(get_latest_release terraform-linters/tflint)"}
INSTALL_DIR=${2:-"/usr/local/bin"}
CMD=tflint
NAME=TFLint

echo -e "\e[34m»»» 📦 \e[32mInstalling \e[33m$NAME v$VERSION\e[0m ..."

curl -sSL "https://github.com/terraform-linters/tflint/releases/download/v${VERSION}/tflint_linux_amd64.zip" -o /tmp/tflint.zip
unzip /tmp/tflint.zip -d /tmp > /dev/null
mkdir -p "$INSTALL_DIR"
mv /tmp/tflint "$INSTALL_DIR"
rm -f /tmp/tflint.zip

echo -e "\n\e[34m»»» 💾 \e[32mInstalled to: \e[33m$(which $CMD)"
echo -e "\e[34m»»» 💡 \e[32mVersion details: \e[39m$($CMD --version)"
