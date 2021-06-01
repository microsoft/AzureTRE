FROM debian:latest

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y curl jq

ARG USER=porter
RUN useradd -ms /bin/bash $USER
USER $USER

# Install Porter & Azure CNAB driver.
ENV ACC_CLOUD='true'
RUN curl https://raw.githubusercontent.com/deislabs/cnab-azure-driver/main/install-in-azure-cloudshell.sh | /bin/bash
ENV ACC_CLOUD=
ENV PATH="/home/$USER/.porter:/home/$USER/.cnab-azure-driver:$PATH"