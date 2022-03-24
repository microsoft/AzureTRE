#!/bin/bash

# Remove apt sources not included in sources.list file
sudo rm /etc/apt/sources.list.d/*

# Update apt packages from configured Nexus sources
sudo apt-get update

# Install xrdp so Guacamole can connect via RDP
sudo apt-get install xrdp -y
sudo adduser xrdp ssl-cert

# Required packages for Docker installation
sudo apt-get install ca-certificates curl gnupg lsb-release
# Get Docker Public key from Nexus
curl -fsSL ${nexus_proxy_url}/repository/docker-public-key/gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/docker-archive-keyring.gpg

# Install desktop environment if image doesn't have one already
if [ ${install_ui} -eq 1 ]; then
  sudo apt-get install xorg xfce4 xfce4-goodies dbus-x11 x11-xserver-utils -y
  echo xfce4-session > ~/.xsession
fi

# Fix for blank screen on DSVM (/sh -> /bash due to conflict with profile.d scripts)
sudo sed -i 's|!/bin/sh|!/bin/bash|g' /etc/xrdp/startwm.sh

# Make sure xrdp service starts up with the system
sudo systemctl enable xrdp


if [ ${shared_storage_access} -eq 1 ]; then
  # Install required packages
  sudo apt-get install autofs

  # Pass in required variables
  resourceGroupName="${resource_group_name}"
  storageAccountName="${storage_account_name}"
  storageAccountKey="${storage_account_key}"
  httpEndpoint="${http_endpoint}"
  fileShareName="${fileshare_name}"
  mntRoot="/fileshares"
  credentialRoot="/etc/smbcredentials"

  mntPath="$mntRoot/$fileShareName"
  smbPath=$(echo $httpEndpoint | cut -c7-$(expr length $httpEndpoint))$fileShareName
  smbCredentialFile="$credentialRoot/$storageAccountName.cred"

  # Create required file paths
  sudo mkdir -p $mntPath
  sudo mkdir -p "/etc/smbcredentials"
  sudo mkdir -p $mntRoot

  ### Auto FS to persist storage
  # Create credential file
  if [ ! -f $smbCredentialFile ]; then
      echo "username=$storageAccountName" | sudo tee $smbCredentialFile > /dev/null
      echo "password=$storageAccountKey" | sudo tee -a $smbCredentialFile > /dev/null
  else
      echo "The credential file $smbCredentialFile already exists, and was not modified."
  fi

  # Change permissions on the credential file so only root can read or modify the password file.
  sudo chmod 600 $smbCredentialFile

  # Configure autofs
  sudo echo "$fileShareName -fstype=cifs,rw,dir_mode=0777,credentials=$smbCredentialFile :$smbPath" > /etc/auto.fileshares
  sudo echo "$mntRoot /etc/auto.fileshares --timeout=60" > /etc/auto.master

  # Restart service to register changes
  sudo systemctl restart autofs

  # Autofs mounts when accessed for 60 seconds.  Folder created for constant visible mount
  sudo ln -s $mntPath "/$fileShareName"
fi

### Anaconda Config
if [ ${conda_config} -eq 1 ]; then
  export PATH="/anaconda/condabin":$PATH
  export PATH="/anaconda/bin":$PATH
  export PATH="/anaconda/envs/py38_default/bin":$PATH
  conda config --add channels ${nexus_proxy_url}/repository/conda/  --system
  conda config --add channels ${nexus_proxy_url}/repository/conda-forge/  --system
  conda config --remove channels defaults --system
  conda config --set channel_alias ${nexus_proxy_url}/repository/conda/  --system
fi
