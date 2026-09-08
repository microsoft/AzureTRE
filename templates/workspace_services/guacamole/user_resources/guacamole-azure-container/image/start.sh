#!/bin/bash
set -euo pipefail

: "${DESKTOP_PASSWORD:?DESKTOP_PASSWORD must be supplied at runtime}"
: "${NEXUS_PROXY_URL:?NEXUS_PROXY_URL must be supplied at runtime}"
if [[ "$NEXUS_PROXY_URL" != https://* || "$NEXUS_PROXY_URL" == *$'\n'* || "$NEXUS_PROXY_URL" == *\"* ]]; then
  echo "Invalid Nexus URL" >&2
  exit 1
fi
printf 'researcher:%s\n' "$DESKTOP_PASSWORD" | chpasswd
unset DESKTOP_PASSWORD STORAGE_EXPLORER_URL RSTUDIO_DOWNLOAD_URL
mkdir -p /run/xrdp /run/dbus /var/log/supervisor /fileshares
chown xrdp:xrdp /run/xrdp
dbus-uuidgen --ensure
openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
  -subj '/CN=tre-desktop' -keyout /etc/xrdp/key.pem -out /etc/xrdp/cert.pem >/dev/null 2>&1
chown root:xrdp /etc/xrdp/key.pem
chmod 640 /etc/xrdp/key.pem
rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources
printf '%s\n' \
  "deb $NEXUS_PROXY_URL/repository/ubuntu/ jammy main restricted universe multiverse" \
  "deb $NEXUS_PROXY_URL/repository/ubuntu/ jammy-updates main restricted universe multiverse" \
  "deb $NEXUS_PROXY_URL/repository/ubuntu-security/ jammy-security main restricted universe multiverse" \
  "deb [signed-by=/usr/share/keyrings/microsoft.gpg] $NEXUS_PROXY_URL/repository/microsoft-apt/ubuntu/22.04/prod jammy main" \
  "deb [signed-by=/usr/share/keyrings/microsoft.gpg] $NEXUS_PROXY_URL/repository/microsoft-apt/repos/edge stable main" \
  "deb [signed-by=/usr/share/keyrings/microsoft.gpg] $NEXUS_PROXY_URL/repository/microsoft-apt/repos/vscode stable main" \
  "deb [signed-by=/usr/share/keyrings/microsoft.gpg] $NEXUS_PROXY_URL/repository/microsoft-apt/repos/azure-cli jammy main" \
  > /etc/apt/sources.list
printf '[global]\nindex-url = %s/repository/pypi/simple\n' "$NEXUS_PROXY_URL" > /etc/pip.conf
printf 'options(repos = c(Nexus = "%s/repository/r-proxy/"))\n' "$NEXUS_PROXY_URL" > /etc/R/Rprofile.site
if [[ -d /fileshares/vm-shared-storage ]]; then
  ln -sfn /fileshares/vm-shared-storage /vm-shared-storage
fi
exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf