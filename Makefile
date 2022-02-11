.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build-api-image push-api-image deploy-tre destroy-tre letsencrypt

SHELL:=/bin/bash
ROOTPATH:=$(shell pwd)

IMAGE_NAME_PREFIX?="microsoft/azuretre"
FULL_CONTAINER_REGISTRY_NAME?="$${ACR_NAME}.azurecr.io"
FULL_IMAGE_NAME_PREFIX:=`echo "${FULL_CONTAINER_REGISTRY_NAME}/${IMAGE_NAME_PREFIX}" | tr A-Z a-z`

target_title = @echo -e "\n\e[34m»»» 🧩 \e[96m$(1)\e[0m..."

all: bootstrap mgmt-deploy images tre-deploy
images: build-and-push-api build-and-push-resource-processor build-and-push-gitea build-and-push-guacamole

build-and-push-api: build-api-image push-api-image
build-and-push-resource-processor: build-resource-processor-vm-porter-image push-resource-processor-vm-porter-image
build-and-push-gitea: build-gitea-image push-gitea-image
build-and-push-guacamole: build-guacamole-image push-guacamole-image

bootstrap:
	$(call target_title, "Bootstrap Terraform") \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ./devops/terraform && ./bootstrap.sh

mgmt-deploy:
	$(call target_title, "Deploying management infrastructure") \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ./devops/terraform && ./deploy.sh

mgmt-destroy:
	$(call target_title, "Destroying management infrastructure") \
	. ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ./devops/terraform && ./destroy.sh

build-api-image:
	$(call target_title, "Building API Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./api_app/_version.py | sed 's/ *= */=/g') \
	&& docker build -t "${FULL_IMAGE_NAME_PREFIX}/api:$${__version__}" ./api_app/

build-resource-processor-vm-porter-image:
	$(call target_title, "Building Resource Processor Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./resource_processor/version.txt | sed 's/ *= */=/g') \
	&& docker build -t "${FULL_IMAGE_NAME_PREFIX}/resource-processor-vm-porter:$${__version__}" -f ./resource_processor/vmss_porter/Dockerfile ./resource_processor/

build-gitea-image:
	$(call target_title, "Building Gitea Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/shared_services/gitea/version.txt | sed 's/ *= */=/g') \
	&& docker build -t "${FULL_IMAGE_NAME_PREFIX}/gitea:$${__version__}" -f ./templates/shared_services/gitea/Dockerfile .

build-guacamole-image:
	$(call target_title, "Building Guacamole Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/workspace_services/guacamole/version.txt | sed 's/ *= */=/g') \
	&& cd ./templates/workspace_services/guacamole/guacamole-server/ \
	&& docker build -t "${FULL_IMAGE_NAME_PREFIX}/guac-server:$${__version__}" -f ./docker/Dockerfile .

push-resource-processor-vm-porter-image:
	$(call target_title, "Pushing Resource Processor Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./resource_processor/version.txt | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "${FULL_IMAGE_NAME_PREFIX}/resource-processor-vm-porter:$${__version__}"

push-api-image:
	$(call target_title, "Pushing API Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./api_app/_version.py | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "${FULL_IMAGE_NAME_PREFIX}/api:$${__version__}"

push-gitea-image:
	$(call target_title, "Pushing Gitea Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/shared_services/gitea/version.txt | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "${FULL_IMAGE_NAME_PREFIX}/gitea:$${__version__}"

push-guacamole-image:
	$(call target_title, "Pushing Guacamole Image") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& source <(grep = ./templates/workspace_services/guacamole/version.txt | sed 's/ *= */=/g') \
	&& az acr login -n $${ACR_NAME} \
	&& docker push "${FULL_IMAGE_NAME_PREFIX}/guac-server:$${__version__}"

tre-deploy:
	$(call target_title, "Deploying TRE") \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& cd ./templates/core/terraform/ && ./deploy.sh

letsencrypt:
	$(call target_title, "Requesting LetsEncrypt SSL certificate") \
	&& . ./devops/scripts/check_dependencies.sh nodocker,certbot \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& pushd ./templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ./devops/scripts/load_env.sh ./templates/core/tre.env \
	&& ./templates/core/terraform/scripts/letsencrypt.sh

tre-stop:
	$(call target_title, "Stopping TRE") \
	&& . ./devops/scripts/check_dependencies.sh azfirewall \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& ./devops/scripts/control_tre.sh stop

tre-start:
	$(call target_title, "Starting TRE") \
	&& . ./devops/scripts/check_dependencies.sh azfirewall \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& ./devops/scripts/control_tre.sh start

tre-destroy:
	$(call target_title, "Destroying TRE") \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& cd ./templates/core/terraform/ && ./destroy.sh

terraform-deploy:
	$(call target_title, "Deploying ${DIR} with Terraform") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./deploy.sh

terraform-import:
	$(call target_title, "Importing ${DIR} with Terraform") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./import.sh

terraform-destroy:
	$(call target_title, "Destroying ${DIR} Service") \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./destroy.sh

lint:
	$(call target_title, "Linting Python and Terraform") && \
	flake8 && \
	cd ./templates && terraform fmt -check -recursive -diff

porter-build:
	$(call target_title, "Building ${DIR} bundle") \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& . ./devops/scripts/set_docker_sock_permission.sh \
	&& cd ${DIR} && porter build --debug

porter-install:
	$(call target_title, "Deploying ${DIR} with Porter") \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter install -p ./parameters.json --cred ./azure.json --allow-docker-host-access --debug

porter-uninstall:
	$(call target_title, "Uninstalling ${DIR} with Porter") \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter uninstall -p ./parameters.json --cred ./azure.json --debug

porter-custom-action:
	$(call target_title, "Deploying ${DIR} with Porter") \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter invoke --action ${ACTION} -p ./parameters.json --cred ./azure.json --debug

porter-publish:
	$(call target_title, "Publishing ${DIR} bundle") \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& az acr login --name $${ACR_NAME}	\
	&& cd ${DIR} \
	&& porter publish --registry "$${ACR_NAME}.azurecr.io" --debug

register-bundle:
	$(call target_title, "Publishing ${DIR} bundle") \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& cd ${DIR} \
	&& ${ROOTPATH}/devops/scripts/publish_register_bundle.sh --acr-name "${ACR_NAME}" --bundle-type "${BUNDLE_TYPE}" --current --insecure --tre_url "${TRE_URL}" --access-token "${TOKEN}"

build-and-register-bundle: porter-build
	$(call target_title, "Building and Publishing ${DIR} bundle") \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& cd ${DIR} \
	&& ${ROOTPATH}/devops/scripts/build_and_register_bundle.sh --acr-name "${ACR_NAME}" --bundle-type "${BUNDLE_TYPE}" --current --insecure --tre_url "${TRE_URL}"

register-bundle-payload:
	$(call target_title, "Publishing ${DIR} bundle") \
	&& ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& cd ${DIR} \
	&& ${ROOTPATH}/devops/scripts/publish_register_bundle.sh --acr-name "${ACR_NAME}" --bundle-type "${BUNDLE_TYPE}" --current

static-web-upload:
	$(call target_title, "Uploading to static website") \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& . ./devops/scripts/load_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ./devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& pushd ./templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ./devops/scripts/load_env.sh ./templates/core/tre.env \
	&& ./templates/core/terraform/scripts/upload_static_web.sh

test-e2e:
	$(call target_title, "Running E2E smoke tests") && \
	export SCOPE="api://${RESOURCE}/user_impersonation" && \
	export WORKSPACE_SCOPE="api://${TEST_WORKSPACE_APP_ID}/user_impersonation" && \
	cd e2e_tests && \
	python -m pytest -m smoke --verify $${IS_API_SECURED:-true} --junit-xml pytest_e2e.xml

setup-local-debugging-api:
	$(call target_title,"Setting up the ability to debug the API") \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& pushd ./templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ./devops/scripts/load_env.sh ./templates/core/tre.env \
	&& . ./devops/scripts/setup_local_api_debugging.sh

register-aad-workspace:
	echo -e "\n\e[34m»»» 🧩 \e[96mSetting up the ability to debug the API\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& pushd ./templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ./devops/scripts/load_env.sh ./templates/core/tre.env \
	&& . ./devops/scripts/register-aad-workspace.sh

