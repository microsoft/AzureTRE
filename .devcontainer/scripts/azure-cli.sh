#!/bin/bash
set -e

CMD=az
NAME="Azure CLI"

echo -e "\e[34m»»» 📦 \e[32mInstalling \e[33m$NAME\e[0m ..."
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# apt cleanup
apt-get clean -y
rm -rf /var/lib/apt/lists/*

echo -e "\n\e[34m»»» 💾 \e[32mInstalled to: \e[33m$(which $CMD)"
echo -e "\e[34m»»» 💡 \e[32mVersion details: \e[39m$($CMD --version)"
