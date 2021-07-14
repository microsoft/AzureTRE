FROM python:3.8

# Azure CLI
RUN apt-get update \
    && apt-get -y install ca-certificates curl apt-transport-https lsb-release gnupg \
    && curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/microsoft.gpg > /dev/null \
    && AZ_REPO=$(lsb_release -cs) \
    && echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" | tee /etc/apt/sources.list.d/azure-cli.list \
    && apt-get update && apt-get -y install azure-cli 

# Install terraform
RUN apt-get update && apt-get install -y gnupg software-properties-common curl \
    && curl -fsSL https://apt.releases.hashicorp.com/gpg |  apt-key add - \
    && apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
    && apt-get update && apt-get install -y terraform 

# Install Porter
RUN export PORTER_HOME=/root/.porter && curl -L https://cdn.porter.sh/latest/install-linux.sh | bash


# Install Docker
RUN apt-get update &&  apt-get install -y  apt-transport-https ca-certificates curl gnupg  lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io

ENV PATH /root/.porter/:$PATH

COPY ./vm_porter/requirements.txt .
RUN pip3 install -r requirements.txt

COPY . /app

WORKDIR /app/vm_porter

CMD ["python","main.py"]