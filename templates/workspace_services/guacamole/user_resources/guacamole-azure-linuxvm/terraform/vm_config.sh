#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
set -o xtrace

echo "init_vm.sh: START"

echo "init_vm.sh: Acquire lock"
timeout 900 bash -c -- 'while fuser /var/lib/dpkg/lock-frontend > /dev/null 2>&1
                            do
                              echo "Waiting to get lock /var/lib/dpkg/lock-frontend..."
                              sleep 5
                            done'

echo "init_vm.sh: Currently installed packages:"
apt list --installed

# Remove apt sources not included in sources.list file
echo "init_vm.sh: APT sources"
rm -f /etc/apt/sources.list.d/*

# shellcheck disable=SC1091
. /etc/os-release
sed -i "s%__VERSION_ID__%$VERSION_ID%" /etc/apt/sources.list
if [ "$VERSION_ID" == "24.04" ]; then
  echo "init_vm.sh: Fix APT for Ubuntu 24.04"
  # azuredatastudio seems to be broken, at least, that's what it reports when we run this...
  apt --fix-broken install -y

  # While we're here, disable bombing out, so we can debug this thing easier
  set +o errexit
  set +o pipefail
fi

# Update apt packages from configured Nexus sources
echo "init_vm.sh: Update OS"
export DEBIAN_FRONTEND=noninteractive
export DEBIAN_PRIORITY=critical
apt upgrade -y
apt-get update -y
rm -f /etc/apt/sources.list.d/* # Again, because of VS Code
apt install -y software-properties-common apt-transport-https wget dirmngr gdebi-core
# apt-get update || true

## Desktop
if [ "$VERSION_ID" == "24.04" ]; then
  echo "init_vm.sh: Desktop"

  # This next line causes problems. Force it to succeed, and hope for the best
  apt install -y xfce4 xfce4-goodies xorg dbus-x11 --fix-missing || true # --fix-missing for Ubuntu 24.04

  ## Install xrdp so Guacamole can connect via RDP
  echo "init_vm.sh: xrdp"
  apt install -y xrdp xorgxrdp xfce4-session
  adduser xrdp ssl-cert
fi
sudo -u "${VM_USER}" -i bash -c 'echo xfce4-session > ~/.xsession'
sudo -u "${VM_USER}" -i bash -c 'echo xset s off >> ~/.xsession'
sudo -u "${VM_USER}" -i bash -c 'echo xset -dpms >> ~/.xsession'

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

if [ "${SHARED_STORAGE_ACCESS}" -eq 1 ]; then
  # Install required packages
  echo "init_vm.sh: Shared storage"
  apt-get install -y autofs

  # Pass in required variables
  storageAccountName="${STORAGE_ACCOUNT_NAME}"
  storageAccountKey="${STORAGE_ACCOUNT_KEY}"
  httpEndpoint="${HTTP_ENDPOINT}"
  fileShareName="${FILESHARE_NAME}"
  # Configure for permanent mount instead of autofs
  mntRoot="/shared-storage"
  credentialRoot="/etc/smbcredentials"

  # shellcheck disable=SC2308
  smbPath=$(echo "$httpEndpoint" | cut -c7-"$(expr length "$httpEndpoint")")$fileShareName
  smbCredentialFile="$credentialRoot/$storageAccountName.cred"

  # Create required file paths
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

## Python 3.8 and Jupyter
echo "init_vm.sh: Jupyter, Edge"
apt install -y jupyter-notebook microsoft-edge-dev

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

# RStudio Desktop
if [ "$VERSION_ID" == "24.04" ]; then
  echo "init_vm.sh: RStudio"
  echo "Sadly, this won't work, there's a problem with the proxy configuration for RStudio"
  # # wget "${NEXUS_PROXY_URL}"/repository/r-studio-download/electron/jammy/amd64/rstudio-2023.12.1-402-amd64.deb -P /tmp/
  # # wget "${NEXUS_PROXY_URL}"/repository/r-studio-download/electron/focal/amd64/rstudio-2023.12.1-402-amd64.deb -P /tmp/
  # # gdebi --non-interactive /tmp/rstudio-2023.12.1-402-amd64.deb

  # # https://download1.rstudio.org/electron/focal/amd64/rstudio-2024.04.2-764-amd64.deb
  # wget "${NEXUS_PROXY_URL}"/repository/r-studio-download/electron/focal/amd64/rstudio-2024.04.2-764-amd64.deb -P /tmp/
  # gdebi --non-interactive /tmp/rstudio-2024.04.2-764-amd64.deb
fi

# R config
echo -e "local({\n    r <- getOption(\"repos\")\n    r[\"Nexus\"] <- \"""${NEXUS_PROXY_URL}\"/repository/r-proxy/\"\n    options(repos = r)\n})" | tee /etc/R/Rprofile.site

### Anaconda Config
if [ "${CONDA_CONFIG}" -eq 1 ]; then
  echo "init_vm.sh: Anaconda"
  if [ -d "/anaconda" ]; then
    export PATH="/anaconda/condabin:/anaconda/bin:$/anaconda/envs/py38_default/bin":$PATH
  fi
  if [ -d "/opt/anaconda" ]; then
    export PATH="/opt/anaconda/condabin:/opt/anaconda/bin":$PATH
  fi
  which conda
  set +o errexit # Don't exit on error if one of these fails
  conda config --add channels "${NEXUS_PROXY_URL}"/repository/conda-mirror/main/ --system
  conda config --add channels "${NEXUS_PROXY_URL}"/repository/conda-repo/main/ --system
  conda config --remove channels defaults --system
  conda config --set channel_alias "${NEXUS_PROXY_URL}"/repository/conda-mirror/ --system

  for repo in $(conda config --show-sources | grep repo.anaconda.com | sort | uniq | awk '{ print $NF }')
  do
    echo "Remove $repo from global config"
    conda config --remove channels $repo --system
  done
  set -o errexit
fi

# Docker install and config
echo "init_vm.sh: Docker"
apt-get remove -y moby-tini || true
apt-get install -y ca-certificates curl gnupg lsb-release
apt-get install -y docker-compose-plugin docker-ce-cli containerd.io jq
apt-get install -y docker-ce
jq -n --arg proxy "${NEXUS_PROXY_URL}:8083" '{"registry-mirrors": [$proxy]}' > /etc/docker/daemon.json
systemctl daemon-reload
systemctl restart docker

echo "init_vm.sh: odds and ends"

# Jupiter Notebook Config
sed -i -e 's/Terminal=true/Terminal=false/g' /usr/share/applications/jupyter-notebook.desktop

# Default Browser
update-alternatives --config x-www-browser

echo "init_vm.sh: environment"
echo "export NEXUS_PROXY_URL=${NEXUS_PROXY_URL}" > /etc/profile.d/99-sde-environment.sh

## Cleanup
echo "init_vm.sh: Cleanup & restart"
rm -f /etc/apt/sources.list.d/* # Again, because of VS Code
set +o xtrace # Avoid Python stack dump from myself
shutdown -r now
