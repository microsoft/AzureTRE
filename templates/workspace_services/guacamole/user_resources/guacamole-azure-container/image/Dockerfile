FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive
ENV EDGE_PACKAGE=microsoft-edge-stable \
    VM_USER=researcher \
    APT_SKU=2204 \
    SHARED_STORAGE_ACCESS=0 \
    CONDA_CONFIG=0 \
    NEXUS_PROXY_URL=https://build.invalid \
    STORAGE_EXPLORER_URL=https://download.microsoft.com/download/A/E/3/AE32C485-B62B-4437-92F7-8B6B2C48CB40/StorageExplorer-linux-x64.tar.gz \
    RSTUDIO_DOWNLOAD_URL=https://download1.rstudio.org

RUN printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d \
    && chmod +x /usr/sbin/policy-rc.d \
    && apt-get update \
    && apt-get install -y --no-install-recommends sudo ca-certificates curl gnupg locales supervisor openssl git \
    && printf 'Defaults env_keep += "DEBIAN_FRONTEND"\n' > /etc/sudoers.d/tre-build \
    && locale-gen en_US.UTF-8 \
    && useradd --create-home --shell /bin/bash --uid 1000 researcher \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft.gpg \
    && printf '%s\n' \
      'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/ubuntu/22.04/prod jammy main' \
      'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/edge stable main' \
      'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/code stable main' \
      'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/azure-cli jammy main' \
      > /etc/apt/sources.list.d/microsoft.list

COPY guacamole-azure-container/image/install.sh /opt/tre/install.sh
RUN bash /opt/tre/install.sh desktop
RUN bash /opt/tre/install.sh edge
RUN bash /opt/tre/install.sh vscode
RUN bash /opt/tre/install.sh azure-cli
RUN bash /opt/tre/install.sh dotnet
RUN bash /opt/tre/install.sh research
RUN bash /opt/tre/install.sh storage-explorer
RUN bash /opt/tre/install.sh rstudio

COPY guacamole-azure-container/image/bootstrap.sh /opt/tre/bootstrap.sh
RUN bash /opt/tre/bootstrap.sh \
    && passwd --lock root \
    && printf 'allowed_users=anybody\nneeds_root_rights=no\n' > /etc/X11/Xwrapper.config \
    && printf 'auth required pam_unix.so\naccount required pam_unix.so\npassword required pam_unix.so\nsession required pam_unix.so\n' > /etc/pam.d/xrdp-sesman \
    && printf '#!/bin/sh\nunset DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR\nexec dbus-run-session -- xfce4-session\n' > /etc/xrdp/startwm.sh \
    && chmod +x /etc/xrdp/startwm.sh

COPY guacamole-azure-container/image/start.sh /opt/tre/start.sh
COPY guacamole-azure-container/image/supervisord.conf /etc/supervisor/conf.d/desktop.conf
RUN chmod +x /opt/tre/start.sh
ENV LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
EXPOSE 3389
ENTRYPOINT ["/opt/tre/start.sh"]