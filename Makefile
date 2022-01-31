.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build-api-image push-api-image deploy-tre destroy-tre letsencrypt

SHELL:=/bin/bash
ROOTPATH:=$(shell pwd)

all: bootstrap mgmt-deploy images tre-deploy
images: build-and-push-api build-and-push-resource-processor build-and-push-gitea build-and-push-guacamole

build-and-push-api: build-api-image push-api-image
build-and-push-resource-processor: build-resource-processor-vm-porter-image push-resource-processor-vm-porter-image
build-and-push-gitea: build-gitea-image push-gitea-image
build-and-push-guacamole: build-guacamole-image push-guacamole-image

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
	&& source <(grep = ./api_app/_version.py | sed 's/ *= */=/g') \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/api:$${__version__}" ./api_app/

build-resource-processor-vm-porter-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Resource Processor Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./resource_processor/version.txt | sed 's/ *= */=/g') \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/resource-processor-vm-porter:$${__version__}" -f ./resource_processor/vmss_porter/Dockerfile ./resource_processor/

build-gitea-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Gitea Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/shared_services/gitea/version.txt | sed 's/ *= */=/g') \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/gitea:$${__version__}" -f ./templates/shared_services/gitea/Dockerfile .

build-guacamole-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Guacamole Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/workspace_services/guacamole/version.txt | sed 's/ *= */=/g') \
	&& cd ./templates/workspace_services/guacamole/guacamole-server/ \
	&& docker build -t "$${ACR_NAME}.azurecr.io/microsoft/azuretre/guac-server:$${__version__}" -f ./docker/Dockerfile .

push-resource-processor-vm-porter-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Resource Processor Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./resource_processor/version.txt | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/resource-processor-vm-porter:$${__version__}"

push-api-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing API Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./api_app/_version.py | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/api:$${__version__}"

push-gitea-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Gitea Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/shared_services/gitea/version.txt | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/gitea:$${__version__}"

push-guacamole-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Guacamole Image\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/workspace_services/guacamole/version.txt | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "$${ACR_NAME}.azurecr.io/microsoft/azuretre/guac-server:$${__version__}"

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
	&& pushd ./templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ./devops/scripts/load_env.sh ./templates/core/tre.env \
	&& ./templates/core/terraform/scripts/letsencrypt.sh

tre-stop:
	echo -e "\n\e[34m»»» 🧩 \e[96mStopping TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh azfirewall \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& ./devops/scripts/control_tre.sh stop

tre-start:
	echo -e "\n\e[34m»»» 🧩 \e[96mStarting TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh azfirewall \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& ./devops/scripts/control_tre.sh start

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

terraform-format:
	echo -e "\n\e[34m»»» 🧩 \e[96mLinting Terraform\e[0m..." \
	&& cd ./templates && terraform fmt -check -recursive -diff

porter-build:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding ${DIR} bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
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

porter-custom-action:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying ${DIR} with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter invoke --action ${ACTION} -p ./parameters.json --cred ./azure.json --debug

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

build-and-register-bundle: porter-build
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding and Publishing ${DIR} bundle\e[0m..." \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& cd ${DIR} \
	&& ${ROOTPATH}/devops/scripts/build_and_register_bundle.sh --acr-name $${ACR_NAME} --bundle-type $${BUNDLE_TYPE} --current --insecure --tre_url $${TRE_URL}

register-bundle-payload:
	echo -e "\n\e[34m»»» 🧩 \e[96mPublishing ${DIR} bundle\e[0m..." \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& cd ${DIR} \
	&& ${ROOTPATH}/devops/scripts/publish_register_bundle.sh --acr-name $${ACR_NAME} --bundle-type ${BUNDLE_TYPE} --current

static-web-upload:
	echo -e "\n\e[34m»»» 🧩 \e[96mUploading to static website\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& pushd ./templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ./devops/scripts/load_env.sh ./templates/core/tre.env \
	&& ./templates/core/terraform/scripts/upload_static_web.sh

test-e2e:
	export SCOPE="api://${RESOURCE}/user_impersonation" && \
	export WORKSPACE_SCOPE="api://${TEST_WORKSPACE_APP_ID}/user_impersonation" && \
	cd e2e_tests && \
	python -m pytest -m smoke --junit-xml pytest_e2e.xml
