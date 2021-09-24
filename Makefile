.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build-api-image push-api-image deploy-tre destroy-tre letsencrypt

SHELL:=/bin/bash
ROOTPATH:=$(shell pwd)

all: bootstrap mgmt-deploy build-api-image push-api-image build-resource-processor-vm-porter-image push-resource-processor-vm-porter-image build-gitea-image push-gitea-image build-guacamole-image push-guacamole-image tre-deploy

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
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/api:$${IMAGE_TAG}" ./api_app/

build-resource-processor-vm-porter-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Resource Processor Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/resource-processor-vm-porter:$${IMAGE_TAG}" -f ./resource_processor/vmss_porter/Dockerfile ./resource_processor/

build-gitea-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Gitea Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/gitea:$${IMAGE_TAG}" -f ./templates/shared_services/gitea/Dockerfile .

build-guacamole-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Guacamole Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& cd ./templates/workspace_services/guacamole/guacamole-server/ \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/guac-server:$${IMAGE_TAG}" -f ./docker/Dockerfile .

push-resource-processor-vm-porter-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Resource Processor Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/resource-processor-vm-porter:$${IMAGE_TAG}"

push-api-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing API Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/api:$${IMAGE_TAG}"

push-gitea-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Gitea Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/gitea:$${IMAGE_TAG}"

push-guacamole-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Guacamole Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/guac-server:$${IMAGE_TAG}"

tre-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& cd ./templates/core/terraform/ && ./deploy.sh

letsencrypt:
	echo -e "\n\e[34m»»» 🧩 \e[96mRequesting LetsEncrypt SSL certificate\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker,certbot \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& cd ./templates/core/terraform/ && . ./outputs.sh \
	&& cd ./scripts/ && ./letsencrypt.sh

tre-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
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

terraform-import:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying ${DIR} with Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./import.sh

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

register-bundle:
	echo -e "\n\e[34m»»» 🧩 \e[96mPublishing ${DIR} bundle\e[0m..." \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& cd ${DIR} \
	&& ${ROOTPATH}/devops/scripts/publish_register_bundle.sh --acr-name $${ACR_NAME} --bundle-type $${BUNDLE_TYPE} --current --insecure --tre_url $${TRE_URL} --access-token $${TOKEN}
