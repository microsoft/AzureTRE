#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

: "${VM_USER:?VM_USER must be set}"
: "${NEXUS_PROXY_URL:?NEXUS_PROXY_URL must be set}"

mkdir -p /opt/vscode/user-data /opt/vscode/extensions

chmod 666 /etc/profile
cat >> /etc/profile <<'EOF'
export DOTNET_ROOT=/usr/share/dotnet
export PATH=$PATH:/usr/share/dotnet
EOF
chmod 644 /etc/profile

cat > /usr/share/applications/storage-explorer.desktop <<'EOF'
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
EOF

cat > /etc/R/Rprofile.site <<EOF
local({
    r <- getOption("repos")
    r["Nexus"] <- "${NEXUS_PROXY_URL}/repository/r-proxy/"
    options(repos = r)
})
EOF

sed -i -e 's/Terminal=true/Terminal=false/g' /usr/share/applications/jupyter-notebook.desktop
cat > /usr/local/bin/tre-edge <<'EOF'
#!/bin/sh
exec /usr/bin/microsoft-edge-stable \
  --password-store=basic \
  --no-first-run \
  --no-default-browser-check \
  --disable-dev-shm-usage \
  --disable-gpu \
  --disable-quic \
  "$@"
EOF
chmod +x /usr/local/bin/tre-edge
sed -i 's|/usr/bin/microsoft-edge-stable|/usr/local/bin/tre-edge|g' /usr/share/applications/microsoft-edge.desktop
update-alternatives --install /usr/bin/x-www-browser x-www-browser /usr/local/bin/tre-edge 200
update-alternatives --set x-www-browser /usr/local/bin/tre-edge
mkdir -p /etc/xdg/xfce4 /usr/share/xfce4/helpers "/home/${VM_USER}/.config/xfce4"
cat > /etc/xdg/mimeapps.list <<'EOF'
[Default Applications]
text/html=microsoft-edge.desktop
x-scheme-handler/http=microsoft-edge.desktop
x-scheme-handler/https=microsoft-edge.desktop
EOF
cat > /usr/share/xfce4/helpers/microsoft-edge.desktop <<'EOF'
[Desktop Entry]
Version=1.0
Icon=microsoft-edge
Type=X-XFCE-Helper
Name=Microsoft Edge
StartupNotify=false
X-XFCE-Binaries=tre-edge;microsoft-edge-stable;microsoft-edge;
X-XFCE-Category=WebBrowser
X-XFCE-Commands=/usr/local/bin/tre-edge;
X-XFCE-CommandsWithParameter=/usr/local/bin/tre-edge "%s";
EOF
cat > "/home/${VM_USER}/.config/xfce4/helpers.rc" <<'EOF'
WebBrowser=microsoft-edge
EOF
chown -R "${VM_USER}:${VM_USER}" "/home/${VM_USER}/.config"

mkdir -p /etc/polkit-1/localauthority/50-local.d
cat > /etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla <<'EOF'
[Allow Colord all Users]
Identity=unix-user:*
Action=org.freedesktop.color-manager.create-device;org.freedesktop.color-manager.create-profile;org.freedesktop.color-manager.delete-device;org.freedesktop.color-manager.delete-profile;org.freedesktop.color-manager.modify-device;org.freedesktop.color-manager.modify-profile
ResultAny=no
ResultInactive=no
ResultActive=yes
EOF

adduser xrdp ssl-cert
sudo -u "$VM_USER" -i bash -c 'echo xfce4-session > ~/.xsession'
sudo -u "$VM_USER" -i bash -c 'echo xset s off >> ~/.xsession'
sudo -u "$VM_USER" -i bash -c 'echo xset -dpms >> ~/.xsession'
  sed -i \
    -e 's|^Exec=.*|Exec=/usr/local/bin/tre-edge %u|' \
    -e 's|^Icon=.*|Icon=microsoft-edge|' \
    -e 's|^Name=.*|Name=Microsoft Edge|' \
    /usr/share/applications/xfce4-web-browser.desktop
sudo -u "$VM_USER" -i bash -c 'echo Xft.dpi: 192 >> ~/.Xresources'
sed -i 's|!/bin/sh|!/bin/bash|g' /etc/xrdp/startwm.sh
