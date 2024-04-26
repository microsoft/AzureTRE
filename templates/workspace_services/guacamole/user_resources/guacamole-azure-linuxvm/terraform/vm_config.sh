#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
set -o xtrace

# Remove apt sources not included in sources.list file
sudo rm -f /etc/apt/sources.list.d/*

# Update apt packages from configured Nexus sources
echo "init_vm.sh: START"
sudo apt update || true
sudo apt install -y gnupg2 software-properties-common apt-transport-https wget dirmngr gdebi-core
sudo apt-get update || true

## Desktop
echo "init_vm.sh: Desktop"
sudo systemctl start gdm3 || true
DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true
DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true dpkg-reconfigure gdm3 || true
sudo apt install -y xfce4 xfce4-goodies xorg dbus-x11 x11-xserver-utils
echo /usr/sbin/gdm3 > /etc/X11/default-display-manager

## Install xrdp so Guacamole can connect via RDP
echo "init_vm.sh: xrdp"
sudo apt install -y xrdp xorgxrdp xfce4-session
sudo adduser xrdp ssl-cert
sudo -u "${VM_USER}" -i bash -c 'echo xfce4-session > ~/.xsession'
sudo -u "${VM_USER}" -i bash -c 'echo xset s off > ~/.xsession'

# Make sure xrdp service starts up with the system
sudo systemctl enable xrdp
sudo service xrdp restart

## Python 3.8 and Jupyter
sudo apt install -y jupyter-notebook microsoft-edge-dev

## VS Code
echo "init_vm.sh: VS Code"
sudo apt install -y code 
sudo apt install -y gvfs-bin || true

echo "init_vm.sh: Folders"
sudo mkdir -p /opt/vscode/user-data
sudo mkdir -p /opt/vscode/extensions

# echo "init_vm.sh: azure-cli"
sudo apt install azure-cli -y

# TODO: need to look at proxy extentions
## VSCode Extensions
# echo "init_vm.sh: VSCode extensions"
# code --extensions-dir="/opt/vscode/extensions" --user-data-dir="/opt/vscode/user-data" --install-extension ms-python.python
# code --extensions-dir="/opt/vscode/extensions" --user-data-dir="/opt/vscode/user-data" --install-extension REditorSupport.r
# code --extensions-dir="/opt/vscode/extensions" --user-data-dir="/opt/vscode/user-data" --install-extension RDebugger.r-debugger

## R
echo "init_vm.sh: R Setup"
sudo apt install -y r-base

## RStudio Desktop
# echo "init_vm.sh: RStudio"
# wget https://download1.rstudio.org/desktop/bionic/amd64/rstudio-2022.07.2-576-amd64.deb -P /tmp
# sudo gdebi --non-interactive /tmp/rstudio-2022.07.2-576-amd64.deb

## Azure Storage Explorer
# sudo apt install gnome-keyring -y
# wget -q ${NEXUS_PROXY_URL}/microsoft-download/A/E/3/AE32C485-B62B-4437-92F7-8B6B2C48CB40/StorageExplorer-linux-x64.tar.gz -P /tmp
# sudo mkdir /opt/storage-explorer
# tar -xf /tmp/StorageExplorer-linux-x64.tar.gz -C /opt/storage-explorer
# sudo chmod +x /opt/storage-explorer/*.sh

# Fix for blank screen on DSVM (/sh -> /bash due to conflict with profile.d scripts)
sudo sed -i 's|!/bin/sh|!/bin/bash|g' /etc/xrdp/startwm.sh

if [ "${SHARED_STORAGE_ACCESS}" -eq 1 ]; then
  # Install required packages
  sudo apt-get install autofs -y

  # Pass in required variables
  storageAccountName="${STORAGE_ACCOUNT_NAME}"
  storageAccountKey="${STORAGE_ACCOUNT_KEY}"
  httpEndpoint="${HTTP_ENDPOINT}"
  fileShareName="${FILESHARE_NAME}"
  mntRoot="/fileshares"
  credentialRoot="/etc/smbcredentials"

  mntPath="$mntRoot/$fileShareName"
  # shellcheck disable=SC2308
  smbPath=$(echo "$httpEndpoint" | cut -c7-"$(expr length "$httpEndpoint")")$fileShareName
  smbCredentialFile="$credentialRoot/$storageAccountName.cred"

  # Create required file paths
  sudo mkdir -p "$mntPath"
  sudo mkdir -p "/etc/smbcredentials"
  sudo mkdir -p $mntRoot

  ### Auto FS to persist storage
  # Create credential file
  if [ ! -f "$smbCredentialFile" ]; then
      echo "username=$storageAccountName" | sudo tee "$smbCredentialFile" > /dev/null
      echo "password=$storageAccountKey" | sudo tee -a "$smbCredentialFile" > /dev/null
  else
      echo "The credential file $smbCredentialFile already exists, and was not modified."
  fi

  # Change permissions on the credential file so only root can read or modify the password file.
  sudo chmod 600 "$smbCredentialFile"

  # Configure autofs
  echo "$fileShareName -fstype=cifs,rw,dir_mode=0777,credentials=$smbCredentialFile :$smbPath" | sudo tee /etc/auto.fileshares > /dev/null
  echo "$mntRoot /etc/auto.fileshares --timeout=60" | sudo tee /etc/auto.master > /dev/null

  # Restart service to register changes
  sudo systemctl restart autofs

  # Autofs mounts when accessed for 60 seconds.  Folder created for constant visible mount
  sudo ln -s "$mntPath" "/$fileShareName"
fi

### Anaconda Config
if [ "${CONDA_CONFIG}" -eq 1 ]; then
  echo "init_vm.sh: Anaconda"
  export PATH="/anaconda/condabin":$PATH
  export PATH="/anaconda/bin":$PATH
  export PATH="/anaconda/envs/py38_default/bin":$PATH
  conda config --add channels "${NEXUS_PROXY_URL}"/repository/conda-mirror/main/  --system
  conda config --add channels "${NEXUS_PROXY_URL}"/repository/conda-repo/main/  --system
  conda config --remove channels defaults --system
  conda config --set channel_alias "${NEXUS_PROXY_URL}"/repository/conda-mirror/  --system
fi

# Docker install and config
sudo apt-get remove -y moby-tini || true
sudo apt-get install -y r-base-core
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo apt-get install -y docker-compose-plugin docker-ce-cli containerd.io jq
sudo apt-get install -y docker-ce
jq -n --arg proxy "${NEXUS_PROXY_URL}:8083" '{"registry-mirrors": [$proxy]}' > /etc/docker/daemon.json
sudo systemctl daemon-reload
sudo systemctl restart docker

# R config
sudo echo -e "local({\n    r <- getOption(\"repos\")\n    r[\"Nexus\"] <- \"""${NEXUS_PROXY_URL}\"/repository/r-proxy/\"\n    options(repos = r)\n})" | sudo tee /etc/R/Rprofile.site

# # ## Cleanup
# echo "init_vm.sh: Cleanup"
# sudo apt -y autoremove
# sudo apt install unattended-upgrades

sudo shutdown -r now

sudo service xrdp restart
sudo systemctl enable xrdp
