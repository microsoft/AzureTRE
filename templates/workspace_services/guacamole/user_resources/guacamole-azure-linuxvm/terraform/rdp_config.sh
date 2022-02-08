#!/bin/bash
sudo apt update

# Install xrdp so Guacamole can connect via RDP
sudo apt install xrdp -y
sudo adduser xrdp ssl-cert

# Install desktop environment if image doesn't have one already
if [ ${install_ui} -eq 1 ]; then
  sudo apt install xorg xfce4 xfce4-goodies dbus-x11 x11-xserver-utils -y
  echo xfce4-session > ~/.xsession
fi

# Fix for blank screen on DSVM (/sh -> /bash due to conflict with profile.d scripts)
sudo sed -i 's|!/bin/sh|!/bin/bash|g' /etc/xrdp/startwm.sh

# Make sure xrdp service starts up with the system
sudo systemctl enable xrdp
