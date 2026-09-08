#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

EDGE_PACKAGE=${EDGE_PACKAGE:-microsoft-edge-stable}
STORAGE_EXPLORER_URL=${STORAGE_EXPLORER_URL:-https://download.microsoft.com/download/A/E/3/AE32C485-B62B-4437-92F7-8B6B2C48CB40/StorageExplorer-linux-x64.tar.gz}
RSTUDIO_DOWNLOAD_URL=${RSTUDIO_DOWNLOAD_URL:-https://download1.rstudio.org}

clean_apt() {
  apt-get clean
  rm -rf /var/lib/apt/lists/* /tmp/* /var/log/*
}

install_apt_packages() {
  apt-get update
  apt-get install -y "$@"
  clean_apt
}

case "${1:-}" in
  desktop)
    apt-get update || true
    apt-get upgrade -y
    apt-get install -y \
      apt-transport-https \
      dbus-x11 \
      debconf-utils \
      dirmngr \
      gdebi-core \
      gnome-keyring \
      gnupg2 \
      software-properties-common \
      wget \
      xfce4 \
      xfce4-goodies \
      xfce4-session \
      xorg \
      xorgxrdp \
      x11-xserver-utils \
      xrdp
    apt-get install -y gvfs-bin || true
    apt-get remove xfce4-screensaver -y
    clean_apt
    ;;
  edge)
    install_apt_packages "$EDGE_PACKAGE"
    ;;
  vscode)
    install_apt_packages code
    ;;
  azure-cli)
    install_apt_packages azure-cli
    ;;
  dotnet)
    install_apt_packages dotnet-sdk-8.0
    ;;
  research)
    install_apt_packages jupyter-notebook r-base
    ;;
  storage-explorer)
    wget -q "$STORAGE_EXPLORER_URL" -O /tmp/StorageExplorer-linux-x64.tar.gz
    mkdir -p /opt/storage-explorer
    tar xf /tmp/StorageExplorer-linux-x64.tar.gz -C /opt/storage-explorer
    chmod +x /opt/storage-explorer/*
    rm -rf /tmp/*
    ;;
  rstudio)
    apt-get update
    wget -q "$RSTUDIO_DOWNLOAD_URL/electron/jammy/amd64/rstudio-2023.12.1-402-amd64.deb" -O /tmp/rstudio.deb
    gdebi --non-interactive /tmp/rstudio.deb
    clean_apt
    ;;
  *)
    echo "Usage: $0 {desktop|edge|vscode|azure-cli|dotnet|research|storage-explorer|rstudio}" >&2
    exit 1
    ;;
esac