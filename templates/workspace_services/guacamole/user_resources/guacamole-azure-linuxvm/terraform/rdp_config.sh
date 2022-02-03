#!/bin/bash
sudo apt update
sudo apt install xorg xfce4 xfce4-goodies dbus-x11 x11-xserver-utils -y
echo xfce4-session > ~/.xsession
sudo apt install xrdp -y
sudo adduser xrdp ssl-cert
sudo systemctl enable xrdp
sudo systemctl restart xrdp
