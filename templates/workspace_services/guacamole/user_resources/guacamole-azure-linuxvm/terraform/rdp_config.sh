#!/bin/bash
NEXUS_URL="https://nexus-${tre_id}.azurewebsites.net"
sudo rm -r /var/lib/apt/lists/*
sudo rm /etc/apt/sources.list
echo "deb [trusted=yes] $NEXUS_URL/repository/ubuntu-proxy-repo/ bionic main restricted universe multiverse" >> /etc/apt/sources.list
echo "deb [trusted=yes] $NEXUS_URL/repository/ubuntu-proxy-repo/ bionic-updates main restricted universe multiverse" >> /etc/apt/sources.list
echo "deb [trusted=yes] $NEXUS_URL/repository/ubuntu-security-proxy-repo/ bionic main restricted universe multiverse" >> /etc/apt/sources.list
echo "deb [trusted=yes] $NEXUS_URL/repository/pypi-proxy-repo/ bionic main restricted universe multiverse" >> /etc/apt/sources.list
sudo apt update
sudo apt install xorg xfce4 xfce4-goodies dbus-x11 x11-xserver-utils -y
echo xfce4-session > ~/.xsession
sudo apt install xrdp -y
sudo adduser xrdp ssl-cert
sudo systemctl enable xrdp
sudo systemctl restart xrdp
