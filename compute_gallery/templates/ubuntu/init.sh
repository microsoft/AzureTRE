#!/bin/bash

set -o errexit
set -o pipefail

function log {
  echo  "$(date '+%Y-%m-%d %H:%M') init_vm.sh: $1"
}

log "Running init_vm.sh"
sudo apt-get update

# Install xrdp
log "Install xrdp"
sudo apt-get install xrdp -y
sudo usermod -a -G ssl-cert xrdp 

# Make sure xrdp service starts up with the system
log "Enable xrdp"
sudo systemctl enable xrdp

# Install desktop environment if image doesn't have one already
log "Install XFCE"
sudo apt-get install xorg xfce4 xfce4-goodies dbus-x11 x11-xserver-utils gdebi-core xfce4-screensaver- --yes
echo xfce4-session > ~/.xsession

# Fix for blank screen on DSVM (/sh -> /bash due to conflict with profile.d scripts)
sudo sed -i 's|!/bin/sh|!/bin/bash|g' /etc/xrdp/startwm.sh

# Set the timezone to London
log "Set Timezone"
sudo timedatectl set-timezone Europe/London

# Fix Keyboard Layout
log "Set Keyboard Layout"
sudo sed -i 's/"us"/"gb"/' /etc/default/keyboard

## SMB Client
log "Install SMB Client"
sudo apt-get install smbclient -y

## VS Code
log "Install VS Code"
sudo apt-get install software-properties-common apt-transport-https wget -y
wget -O- https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor | sudo tee /usr/share/keyrings/vscode.gpg
echo deb [arch=amd64 signed-by=/usr/share/keyrings/vscode.gpg] https://packages.microsoft.com/repos/vscode stable main | sudo tee /etc/apt/sources.list.d/vscode.list
sudo apt update
sudo apt install -y code

## Anaconda
log "Install Anaconda"
sudo apt -y install libgl1-mesa-glx libegl1-mesa libxrandr2 libxrandr2 libxss1 libxcursor1 libxcomposite1 libasound2 libxi6 libxtst6
wget https://repo.anaconda.com/archive/Anaconda3-2022.10-Linux-x86_64.sh -P /tmp
chmod +x /tmp/Anaconda3-2022.10-Linux-x86_64.sh
sudo bash /tmp/Anaconda3-2022.10-Linux-x86_64.sh -b -p /opt/anaconda
/opt/anaconda/bin/conda install -y -c anaconda anaconda-navigator

## R
log "Install R"
wget -q https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc -O- | sudo apt-key add -
sudo add-apt-repository -y "deb https://cloud.r-project.org/bin/linux/ubuntu $(lsb_release -cs)-cran40/"
sudo apt update
sudo apt install -y r-base

## RStudio Desktop
log "Install RStudio"
wget -q https://download1.rstudio.org/electron/jammy/amd64/rstudio-2023.03.0-386-amd64.deb -P /tmp
sudo gdebi --non-interactive /tmp/rstudio-2023.03.0-386-amd64.deb

## Azure CLI
log "Install Azure CLI"
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az extension add --name arcdata

## Google Chrome
log "Install Google Chrome"
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -P /tmp
sudo gdebi --non-interactive /tmp/google-chrome-stable_current_amd64.deb

## Docker CE
log "Install Docker CE"
sudo apt-get update &&  sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -m 0755 -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

## Grant access to Colord Policy file to avoid errors on RDP connections
log "Install Colord policy"
sudo cat <<EOT >> /etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla
[Allow Colord All Users]
Identity=unix-user:*
Action=org.freedesktop.color-manager.create-device;org.freedesktop.color-manager.create-profile;org.freedesktop.color-manager.delete-device;org.freedesktop.color-manager.delete-profile;org.freedesktop.color-manager.modify-device;org.freedesktop.color-manager.modify-profile
ResultAny=no
ResultInactive=no
ResultActive=yes
EOT
  
## Install script to run at user login
log "Add User Login Script"
sudo cat <<EOT >> /etc/profile.d/init_user_profile.sh

# Add anaconda to PATH
export PATH=/opt/anaconda/bin:$PATH

# Add user to docker group
sudo usermod -aG docker $USER

if [ ! -f ~/.xsession ]
then
  echo "Setup xsession"
  echo xfce4-session > ~/.xsession
fi

if [ -f ~/.xscreensaver ]
then  # turn off screensaver
  sed -i 's/random/blank/' ~/.xscreensaver
fi
EOT
