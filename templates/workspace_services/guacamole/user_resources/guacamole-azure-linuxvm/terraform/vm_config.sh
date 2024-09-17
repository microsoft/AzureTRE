#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
set -o xtrace

echo "init_vm.sh: I am running as:"
id

echo "init_vm.sh: Acquire lock"
timeout 900 bash -c -- 'while fuser /var/lib/dpkg/lock-frontend > /dev/null 2>&1
                            do
                              echo "Waiting to get lock /var/lib/dpkg/lock-frontend..."
                              sleep 5
                            done'

echo "Currently installed packages:"
apt list --installed

# Remove apt sources not included in sources.list file
echo "init_vm.sh: APT sources"
rm -f /etc/apt/sources.list.d/*

# shellcheck disable=SC1091
. /etc/os-release
sed -i "s%__VERSION_ID__%$VERSION_ID%" /etc/apt/sources.list
if [ "$VERSION_ID" == "24.04" ]; then
  # azuredatastudio seems to be broken, at least, that's what it reports when we fix it...
  apt --fix-broken install -y
fi

# Update apt packages from configured Nexus sources
echo "init_vm.sh: START"
export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical
apt upgrade -y
apt-get update -y
rm -f /etc/apt/sources.list.d/* # Again, because of VS Code
apt install -y software-properties-common apt-transport-https wget dirmngr gdebi-core
# apt-get update || true

## Desktop
echo "init_vm.sh: Desktop"
systemctl start gdm3 || true
DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true dpkg-reconfigure gdm3 || true
# Ubuntu 24.04 seems flaky here, so this line has to be split, and "--fix-missing" added, for good measure
# apt install -y xfce4 xfce4-goodies xorg dbus-x11 x11-xserver-utils
#
# it's this next line, in particular, that causes the problem. Force it to succeed, and hope for the best
apt install -y xfce4 xfce4-goodies xorg dbus-x11 --fix-missing || true # --fix-missing for Ubuntu 24.04
apt install -y x11-xserver-utils --fix-missing # --fix-missing for Ubuntu 24.04
echo /usr/sbin/gdm3 > /etc/X11/default-display-manager

## Install xrdp so Guacamole can connect via RDP
echo "init_vm.sh: xrdp"
apt install -y xrdp xorgxrdp xfce4-session
adduser xrdp ssl-cert
sudo -u "${VM_USER}" -i bash -c 'echo xfce4-session > ~/.xsession'
sudo -u "${VM_USER}" -i bash -c 'echo xset s off >> ~/.xsession'
sudo -u "${VM_USER}" -i bash -c 'echo xset -dpms >> ~/.xsession'

# Make sure xrdp service starts up with the system
systemctl enable xrdp
service xrdp restart

# Prevent screen timeout
echo "init_vm.sh: Preventing Timeout"
mkdir -p /home/"${VM_USER}"/.config/xfce4/xfconf/xfce-perchannel-xml
touch /home/"${VM_USER}"/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-screensaver.xml
chmod 664 /home/"${VM_USER}"/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-screensaver.xml
tee /home/"${VM_USER}"/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-screensaver.xml << END
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-screensaver" version="1.0">
  <property name="saver" type="empty">
    <property name="mode" type="int" value="0"/>
    <property name="enabled" type="bool" value="false"/>
  </property>
  <property name="lock" type="empty">
    <property name="enabled" type="bool" value="false"/>
  </property>
</ channel>
END
chown -Rf "${VM_USER}":"${VM_USER}" /home/"${VM_USER}"/.config

# Fix for blank screen on DSVM (/sh -> /bash due to conflict with profile.d scripts)
sed -i 's|!/bin/sh|!/bin/bash|g' /etc/xrdp/startwm.sh

if [ "${SHARED_STORAGE_ACCESS}" -eq 1 ]; then
  # Install required packages
  echo "init_vm.sh: Shared storage"
  apt-get install autofs -y

  # Pass in required variables
  storageAccountName="${STORAGE_ACCOUNT_NAME}"
  storageAccountKey="${STORAGE_ACCOUNT_KEY}"
  httpEndpoint="${HTTP_ENDPOINT}"
  fileShareName="${FILESHARE_NAME}"
  # Configure for permanent mount instead of autofs
  mntRoot="/shared-storage"
  credentialRoot="/etc/smbcredentials"

  # mntPath="$mntRoot/$fileShareName"
  # shellcheck disable=SC2308
  smbPath=$(echo "$httpEndpoint" | cut -c7-"$(expr length "$httpEndpoint")")$fileShareName
  smbCredentialFile="$credentialRoot/$storageAccountName.cred"

  # Create required file paths
  # mkdir -p "$mntPath"
  mkdir -p $credentialRoot
  mkdir -p $mntRoot

  ### Auto FS to persist storage
  # Create credential file
  if [ ! -f "$smbCredentialFile" ]; then
      echo "username=$storageAccountName" | tee "$smbCredentialFile" > /dev/null
      echo "password=$storageAccountKey" | tee -a "$smbCredentialFile" > /dev/null
  else
      echo "The credential file $smbCredentialFile already exists, and was not modified."
  fi

  # Change permissions on the credential file so only root can read or modify the password file.
  chmod 600 "$smbCredentialFile"

  echo "$smbPath $mntRoot cifs rw,vers=default,dir_mode=0777,file_mode=0777,uid=1000,gid=1000,credentials=$smbCredentialFile 0 0" | tee -a /etc/fstab >/dev/null
  mount $mntRoot
fi

# set +o errexit
# set +o pipefail
# set +o nounset
set -o xtrace

## Python 3.8 and Jupyter
echo "init_vm.sh: Jupyter, Edge"
apt install -y jupyter-notebook microsoft-edge-dev

## VS Code
echo "init_vm.sh: VS Code"
# apt install -y code
# apt install -y gvfs-bin || true

echo "init_vm.sh: Folders"
mkdir -p /opt/vscode/user-data
mkdir -p /opt/vscode/extensions

echo "init_vm.sh: azure-cli"
apt install azure-cli -y

# TODO: need to look at proxy extentions
## VSCode Extensions
# echo "init_vm.sh: VSCode extensions"
# code --extensions-dir="/opt/vscode/extensions" --user-data-dir="/opt/vscode/user-data" --install-extension ms-python.python
# code --extensions-dir="/opt/vscode/extensions" --user-data-dir="/opt/vscode/user-data" --install-extension REditorSupport.r
# code --extensions-dir="/opt/vscode/extensions" --user-data-dir="/opt/vscode/user-data" --install-extension RDebugger.r-debugger

# Azure Storage Explorer
apt install gnome-keyring dotnet-sdk-8.0 -y
wget -q "${NEXUS_PROXY_URL}"/repository/microsoft-download/A/E/3/AE32C485-B62B-4437-92F7-8B6B2C48CB40/StorageExplorer-linux-x64.tar.gz -P /tmp
mkdir -p /opt/storage-explorer
tar xvf /tmp/StorageExplorer-linux-x64.tar.gz -C /opt/storage-explorer
chmod +x /opt/storage-explorer/*

tee /usr/share/applications/storage-explorer.desktop << END
[Desktop Entry]
Name=Storage Explorer
Comment=Azure Storage Explorer
Exec=/opt/storage-explorer/StorageExplorer
Icon=/opt/storage-explorer/resources/app/out/app/icon.png
Terminal=false
Type=Application
StartupNotify=false
StartupWMClass=Code
Categories=Development;
END

## R
echo "init_vm.sh: R Setup"
apt install -y r-base

# RStudio Desktop
echo "init_vm.sh: RStudio"
wget "${NEXUS_PROXY_URL}"/repository/r-studio-download/electron/jammy/amd64/rstudio-2023.12.1-402-amd64.deb -P /tmp/
# wget "${NEXUS_PROXY_URL}"/repository/r-studio-download/electron/focal/amd64/rstudio-2023.12.1-402-amd64.deb -P /tmp/
gdebi --non-interactive /tmp/rstudio-2023.12.1-402-amd64.deb

### Anaconda Config
if [ "${CONDA_CONFIG}" -eq 1 ]; then
  echo "init_vm.sh: Anaconda"
  if [ -d "/anaconda" ]; then
    export PATH="/anaconda/condabin:/anaconda/bin:$/anaconda/envs/py38_default/bin":$PATH
  fi
  if [ -d "/opt/anaconda" ]; then
    export PATH="/opt/anaconda/condabin:/opt/anaconda/bin":$PATH
  fi
  conda config --add channels "${NEXUS_PROXY_URL}"/repository/conda-mirror/main/  --system
  conda config --add channels "${NEXUS_PROXY_URL}"/repository/conda-repo/main/  --system
  conda config --remove channels defaults --system
  conda config --set channel_alias "${NEXUS_PROXY_URL}"/repository/conda-mirror/  --system
fi

# Docker install and config
apt-get remove -y moby-tini || true
apt-get install -y r-base-core
apt-get install -y ca-certificates curl gnupg lsb-release
apt-get install -y docker-compose-plugin docker-ce-cli containerd.io jq
apt-get install -y docker-ce
jq -n --arg proxy "${NEXUS_PROXY_URL}:8083" '{"registry-mirrors": [$proxy]}' > /etc/docker/daemon.json
systemctl daemon-reload
systemctl restart docker

# R config
echo -e "local({\n    r <- getOption(\"repos\")\n    r[\"Nexus\"] <- \"""${NEXUS_PROXY_URL}\"/repository/r-proxy/\"\n    options(repos = r)\n})" | tee /etc/R/Rprofile.site

# Jupiter Notebook Config
sed -i -e 's/Terminal=true/Terminal=false/g' /usr/share/applications/jupyter-notebook.desktop

# Default Browser
update-alternatives --config x-www-browser

echo "init_vm.sh: environment"
echo "export NEXUS_PROXY_URL=${NEXUS_PROXY_URL}" > /etc/profile.d/99-sde-environment.sh
env | sort

## Cleanup
echo "init_vm.sh: Cleanup"
rm -f /etc/apt/sources.list.d/* # Again, because of VS Code
shutdown -r now
