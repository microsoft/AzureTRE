#!/bin/bash
NEXUS_URL="https://nexus-${tre_id}.azurewebsites.net"
 sudo rm -r /var/lib/apt/lists/*
 sudo rm /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/ubuntu_proxy_repo bionic main restricted" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/ubuntu_proxy_repo bionic universe" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/ubuntu_proxy_repo bionic multiverse" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/ubuntu_security_proxy_repo bionic main restricted" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/ubuntu_security_proxy_repo bionic universe" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/ubuntu_security_proxy_repo bionic multiverse" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/pypi-proxy-repo bionic main restricted" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/pypi-proxy-repo bionic universe" >> /etc/apt/sources.list
 echo "deb $NEXUS_URL/service/rest/v1/repositories/apt/proxy/pypi-proxy-repo bionic multiverse" >> /etc/apt/sources.list
 sudo apt-get update
 sudo DEBIAN_FRONTEND=noninteractive apt-get install ubuntu-gnome-desktop -yq
 sudo apt-get install xrdp -y
 sudo adduser xrdp ssl-cert
 sudo systemctl enable xrdp
 sudo reboot
