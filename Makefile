.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build-api-image push-api-image build-cnab-image push-cnab-image deploy-tre destroy-tre letsencrypt

SHELL:=/bin/bash

all: bootstrap mgmt-deploy build-api-image push-api-image build-resource-processor-vm-porter-image push-resource-processor-vm-porter-image build-cnab-image push-cnab-image tre-deploy

bootstrap:
	echo -e "\n\e[34m»»» 🧩 \e[96mBootstrap Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ./devops/terraform && ./bootstrap.sh

mgmt-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying management infrastructure\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ./devops/terraform && ./deploy.sh

mgmt-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying management infrastructure\e[0m..." \
	. ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ./devops/terraform && ./destroy.sh

build-api-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding API Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/management-api:$${IMAGE_TAG}" ./management_api_app/

build-cnab-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding CNAB Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/cnab-aci:$${IMAGE_TAG}" ./CNAB_container/


build-resource-processor-vm-porter-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/resource-processor-vm-porter:$${IMAGE_TAG}" -f ./processor_function/vm_porter/Dockerfile ./processor_function/

push-resource-processor-vm-porter-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/resource-processor-vm-porter:$${IMAGE_TAG}"

push-api-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/management-api:$${IMAGE_TAG}"

push-cnab-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/cnab-aci:$${IMAGE_TAG}"

tre-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& cd ./templates/core/terraform/ && ./deploy.sh \
	&& cd ../../../ && ./devops/scripts/set_contributor_sp_secrets.sh

deploy-processor-function:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying processor function\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& cd ./processor_function && func azure functionapp publish "processor-func-$${TRE_ID}" --python

letsencrypt:
	echo -e "\n\e[34m»»» 🧩 \e[96mRequesting LetsEncrypt SSL certificate\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker,certbot \
	&& chmod 755 ./devops/scripts/letsencrypt.sh ./devops/scripts/auth-hook.sh ./devops/scripts/cleanup-hook.sh \
	&& . ./devops/scripts/get-coreenv.sh \
	&& ./devops/scripts/letsencrypt.sh

tre-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& cd ./templates/core/terraform/ && ./destroy.sh

terraform-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying ${DIR} with Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./deploy.sh

terraform-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying ${DIR} Service\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./destroy.sh


porter-build:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding ${DIR} bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter build --debug

porter-install:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying ${DIR} with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter install -p ./parameters.json --cred ./azure.json --allow-docker-host-access --debug

porter-uninstall:
	echo -e "\n\e[34m»»» 🧩 \e[96mUninstalling ${DIR} with Porter\e[0m..." \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter uninstall -p ./parameters.json --cred ./azure.json --debug

porter-publish:
	echo -e "\n\e[34m»»» 🧩 \e[96mPublishing ${DIR} bundle\e[0m..." \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& az acr login --name $${ACR_NAME}	\
	&& cd ${DIR} \
	&& porter publish --registry "$${ACR_NAME}.azurecr.io" --debug
