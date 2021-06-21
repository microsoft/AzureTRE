FROM mcr.microsoft.com/azure-cli

ARG USER=porter
RUN apk add --update docker openrc
RUN rc-update add docker boot
RUN adduser -S $USER -s /bin/bash
USER $USER

COPY azure.json /home/$USER/

# Install Porter & Azure CNAB driver.
ENV ACC_CLOUD='true'
RUN curl https://raw.githubusercontent.com/deislabs/cnab-azure-driver/main/install-in-azure-cloudshell.sh | /bin/bash
RUN source ${HOME}/.bashrc
ENV ACC_CLOUD=
ENV PATH="/home/$USER/.porter:/home/$USER/.cnab-azure-driver:$PATH"
