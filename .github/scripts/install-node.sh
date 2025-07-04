#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

VERSION=${1:-"16"}
CMD=node
NAME="Node.js"

echo -e "\e[34m»»» 📦 \e[32mInstalling \e[33m$NAME \e[35mv$VERSION\e[0m ..."

curl -sL "https://deb.nodesource.com/setup_${VERSION}.x" | sudo -E bash -
sudo apt install -y nodejs

echo -e "\n\e[34m»»» 💾 \e[32mInstalled to: \e[33m$(which $CMD)"
echo -e "\e[34m»»» 💡 \e[32mNode version details: \e[39m$($CMD --version)"
echo -e "\e[34m»»» 💡 \e[32mNPM version details: \e[39m$(npm --version)"
