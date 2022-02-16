#!/bin/bash
sudo apt-get update

# Install xrdp so Guacamole can connect via RDP
sudo apt-get install xrdp -y
sudo adduser xrdp ssl-cert

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
  mntRoot="/mount"
  credentialRoot="/etc/smbcredentials"

  mntPath="$mntRoot/$storageAccountName/$fileShareName"
  smbPath=$(echo $httpEndpoint | cut -c7-$(expr length $httpEndpoint))$fileShareName
  smbCredentialFile="$credentialRoot/$storageAccountName.cred"

  # Create required file paths
  sudo mkdir -p $mntPath
  sudo mkdir -p "/etc/smbcredentials"
  sudo mkdir -p $mntRoot

  # Initial Mount
  sudo mount -t cifs $smbPath $mntPath -o username=$storageAccountName,password=$storageAccountKey,serverino
  
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
  sudo echo "$fileShareName -fstype=cifs,credentials=$smbCredentialFile :$smbPath" > /etc/auto.fileshares
  sudo echo "/fileshares /etc/auto.fileshares --timeout=60" > /etc/auto.master

  # Restart service to register changes
  sudo systemctl restart autofs

  # read/write/execute to admin user and current group (current group will be root)
  sudo chown ${username} $mntPath
  sudo chmod g+twx $mntPath
fi
