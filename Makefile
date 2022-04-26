.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build-api-image push-api-image deploy-tre destroy-tre letsencrypt

SHELL:=/bin/bash
MAKEFILE_FULLPATH := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIR := $(dir $(MAKEFILE_FULLPATH))
IMAGE_NAME_PREFIX?="microsoft/azuretre"
FULL_CONTAINER_REGISTRY_NAME?="$${ACR_NAME}.azurecr.io"
FULL_IMAGE_NAME_PREFIX:=`echo "${FULL_CONTAINER_REGISTRY_NAME}/${IMAGE_NAME_PREFIX}" | tr A-Z a-z`

target_title = @echo -e "\n\e[34m»»» 🧩 \e[96m$(1)\e[0m..."

all: bootstrap mgmt-deploy images tre-deploy
images: build-and-push-api build-and-push-resource-processor build-and-push-gitea build-and-push-guacamole build-and-push-mlflow

build-and-push-api: build-api-image push-api-image
build-and-push-resource-processor: build-resource-processor-vm-porter-image push-resource-processor-vm-porter-image
build-and-push-gitea: build-gitea-image push-gitea-image
build-and-push-guacamole: build-guacamole-image push-guacamole-image
build-and-push-mlflow: build-mlflow-image push-mlflow-image
tre-deploy: deploy-core deploy-shared-services db-migrate show-core-output
deploy-shared-services:
	$(MAKE) firewall-install \
	&& . ./devops/scripts/load_env.sh ./templates/core/.env \
	&& if [ "$${DEPLOY_GITEA}" == "true" ]; then $(MAKE) gitea-install; fi \
	&& if [ "$${DEPLOY_NEXUS}" == "true" ]; then $(MAKE) nexus-install; fi

# to move your environment from the single 'core' deployment (which includes the firewall)
# toward the shared services model, where it is split out - run the following make target before a tre-deploy
# This will remove + import the resource state into a shared service
migrate-firewall-state: prepare-tf-state

bootstrap:
	$(call target_title, "Bootstrap Terraform") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ${CURRENT_DIR}/devops/terraform && ./bootstrap.sh

mgmt-deploy:
	$(call target_title, "Deploying management infrastructure") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ${CURRENT_DIR}/devops/terraform && ./deploy.sh

mgmt-destroy:
	$(call target_title, "Destroying management infrastructure") \
	. ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& cd ${CURRENT_DIR}/devops/terraform && ./destroy.sh

# A recipe for building images. Parameters:
# 1. Image name suffix
# 2. Version file path
# 3. Docker file path
# 4. Docker context path
# Example: $(call build_image,"api","./api_app/_version.py","api_app/Dockerfile","./api_app/")
# The CI_CACHE_ACR_NAME is an optional container registry used for caching in addition to what's in ACR_NAME
define build_image
$(call target_title, "Building $(1) Image") \
&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh \
&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
&& . ${CURRENT_DIR}/devops/scripts/set_docker_sock_permission.sh \
&& source <(grep = $(2) | sed 's/ *= */=/g') \
&& az acr login -n $${ACR_NAME} \
&& if [ -n "$${CI_CACHE_ACR_NAME:-}" ]; then \
	az acr login -n $${CI_CACHE_ACR_NAME}; \
	ci_cache="--cache-from $${CI_CACHE_ACR_NAME}.azurecr.io/${IMAGE_NAME_PREFIX}/$(1):$${__version__}"; fi \
&& docker build -t ${FULL_IMAGE_NAME_PREFIX}/$(1):$${__version__} --build-arg BUILDKIT_INLINE_CACHE=1 \
	--cache-from ${FULL_IMAGE_NAME_PREFIX}/$(1):$${__version__} $${ci_cache:-} -f $(3) $(4)
endef

build-api-image:
	$(call build_image,"api","${CURRENT_DIR}/api_app/_version.py","${CURRENT_DIR}/api_app/Dockerfile","${CURRENT_DIR}/api_app/")

build-resource-processor-vm-porter-image:
	$(call build_image,"resource-processor-vm-porter","${CURRENT_DIR}/resource_processor/version.txt","${CURRENT_DIR}/resource_processor/vmss_porter/Dockerfile","${CURRENT_DIR}/resource_processor/")

build-gitea-image:
	$(call build_image,"gitea","${CURRENT_DIR}/templates/shared_services/gitea/version.txt","${CURRENT_DIR}/templates/shared_services/gitea/Dockerfile","${CURRENT_DIR}/templates/shared_services/gitea/")

build-gitea-workspace-service-image:
	$(call build_image,"gitea-workspace-service","${CURRENT_DIR}/templates/workspace_services/gitea/version.txt","${CURRENT_DIR}/templates/workspace_services/gitea/docker/Dockerfile","${CURRENT_DIR}/templates/workspace_services/gitea/docker/")

build-guacamole-image:
	$(call build_image,"guac-server","${CURRENT_DIR}/templates/workspace_services/guacamole/version.txt","${CURRENT_DIR}/templates/workspace_services/guacamole/guacamole-server/docker/Dockerfile","${CURRENT_DIR}/templates/workspace_services/guacamole/guacamole-server")

build-mlflow-image:
	$(call build_image,"mlflow-server","${CURRENT_DIR}/templates/workspace_services/mlflow/mlflow-server/version.txt","${CURRENT_DIR}/templates/workspace_services/mlflow/mlflow-server/docker/Dockerfile","${CURRENT_DIR}/templates/workspace_services/mlflow/mlflow-server")

firewall-install:
	$(MAKE) bundle-build DIR=${CURRENT_DIR}/templates/shared_services/firewall/ \
	&& $(MAKE) bundle-publish DIR=${CURRENT_DIR}/templates/shared_services/firewall/ \
	&& $(MAKE) bundle-register DIR="${CURRENT_DIR}/templates/shared_services/firewall" BUNDLE_TYPE=shared_service \
	&& $(MAKE) deploy-shared-service DIR=${CURRENT_DIR}/templates/shared_services/firewall/ BUNDLE_TYPE=shared_service

nexus-install:
	$(MAKE) bundle-build DIR=${CURRENT_DIR}/templates/shared_services/sonatype-nexus/ \
	&& $(MAKE) bundle-publish DIR=${CURRENT_DIR}/templates/shared_services/sonatype-nexus/ \
	&& $(MAKE) bundle-register DIR="${CURRENT_DIR}/templates/shared_services/sonatype-nexus" BUNDLE_TYPE=shared_service \
	&& $(MAKE) deploy-shared-service DIR=${CURRENT_DIR}/templates/shared_services/sonatype-nexus/ BUNDLE_TYPE=shared_service

gitea-install:
	$(MAKE) bundle-build DIR=${CURRENT_DIR}/templates/shared_services/gitea/ \
	&& $(MAKE) bundle-publish DIR=${CURRENT_DIR}/templates/shared_services/gitea/ \
	&& $(MAKE) bundle-register DIR="${CURRENT_DIR}/templates/shared_services/gitea" BUNDLE_TYPE=shared_service \
	&& $(MAKE) deploy-shared-service DIR=${CURRENT_DIR}/templates/shared_services/gitea/ BUNDLE_TYPE=shared_service

# A recipe for pushing images. Parameters:
# 1. Image name suffix
# 2. Version file path
# Example: $(call push_image,"api","./api_app/_version.py")
define push_image
$(call target_title, "Pushing $(1) Image") \
&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh \
&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
&& . ${CURRENT_DIR}/devops/scripts/set_docker_sock_permission.sh \
&& source <(grep = $(2) | sed 's/ *= */=/g') \
&& az acr login -n $${ACR_NAME} \
&& docker push "${FULL_IMAGE_NAME_PREFIX}/$(1):$${__version__}"
endef

push-api-image:
	$(call push_image,"api","./api_app/_version.py")

push-resource-processor-vm-porter-image:
	$(call push_image,"resource-processor-vm-porter","${CURRENT_DIR}/resource_processor/version.txt")

push-gitea-image:
	$(call push_image,"gitea","${CURRENT_DIR}/templates/shared_services/gitea/version.txt")

push-gitea-workspace-service-image:
	$(call push_image,"gitea-workspace-service","${CURRENT_DIR}/templates/workspace_services/gitea/version.txt")

push-guacamole-image:
	$(call push_image,"guac-server","${CURRENT_DIR}/templates/workspace_services/guacamole/version.txt")

push-mlflow-image:
	$(call push_image,"mlflow-server","${CURRENT_DIR}/templates/workspace_services/mlflow/mlflow-server/version.txt")

# # These targets are for a graceful migration of Firewall
# # from terraform state in Core to a Shared Service.
# # See https://github.com/microsoft/AzureTRE/issues/1177
prepare-tf-state:
	$(call target_title, "Preparing terraform state") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& pushd ${CURRENT_DIR}/templates/core/terraform > /dev/null && ../../shared_services/firewall/terraform/remove_state.sh && popd > /dev/null \
	&& pushd ${CURRENT_DIR}/templates/shared_services/firewall/terraform > /dev/null && ./import_state.sh && popd > /dev/null
# / End migration targets

deploy-core: tre-start
	$(call target_title, "Deploying TRE") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& if [[ "$${TF_LOG}" == "DEBUG" ]]; then echo "TF DEBUG set - output supressed - see tflogs container for log file" && cd ${CURRENT_DIR}/templates/core/terraform/ && ./deploy.sh 1>/dev/null 2>/dev/null; else cd ${CURRENT_DIR}/templates/core/terraform/ && ./deploy.sh; fi;

letsencrypt:
	$(call target_title, "Requesting LetsEncrypt SSL certificate") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker,certbot \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& pushd ${CURRENT_DIR}/templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/private.env \
	&& ${CURRENT_DIR}/templates/core/terraform/scripts/letsencrypt.sh

tre-start:
	$(call target_title, "Starting TRE") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& ${CURRENT_DIR}/devops/scripts/control_tre.sh start

tre-stop:
	$(call target_title, "Stopping TRE") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& ${CURRENT_DIR}/devops/scripts/control_tre.sh stop

tre-destroy:
	$(call target_title, "Destroying TRE") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/destroy_env_no_terraform.sh

terraform-deploy:
	$(call target_title, "Deploying ${DIR} with Terraform") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./deploy.sh

terraform-import:
	$(call target_title, "Importing ${DIR} with Terraform") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./import.sh

terraform-destroy:
	$(call target_title, "Destroying ${DIR} Service") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./destroy.sh

# This will validate all files, not only the changed ones as the CI version does.
lint:
	$(call target_title, "Linting")
	@terraform fmt -check -recursive -diff
	@echo "You might not see much on the screen for a few minutes..."
	@# LOG_LEVEL=NOTICE reduces noise but it might also seem like the process is stuck - it's not...
	@docker run --name superlinter --pull=always --rm \
		-e RUN_LOCAL=true \
		-e LOG_LEVEL=NOTICE \
		-e VALIDATE_MARKDOWN=true \
		-e VALIDATE_PYTHON_FLAKE8=true \
		-e VALIDATE_YAML=true \
		-e VALIDATE_TERRAFORM_TFLINT=true \
		-e VALIDATE_JAVA=true \
		-e JAVA_FILE_NAME=checkstyle.xml \
		-e VALIDATE_BASH=true \
		-e VALIDATE_BASH_EXEC=true \
		-e VALIDATE_GITHUB_ACTIONS=true \
		-v $${LOCAL_WORKSPACE_FOLDER}:/tmp/lint \
		github/super-linter:slim-v4

bundle-build:
	$(call target_title, "Building ${DIR} bundle with Porter") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh porter \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ${DIR}/.env \
	&& . ${CURRENT_DIR}/devops/scripts/set_docker_sock_permission.sh \
	&& cd ${DIR} && porter build --debug

bundle-install:
	$(call target_title, "Deploying ${DIR} with Porter") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh porter \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter install -p ./parameters.json \
		--cred ${CURRENT_DIR}/resource_processor/vmss_porter/arm_auth_local_debugging.json \
		--cred ${CURRENT_DIR}/resource_processor/vmss_porter/aad_auth_local_debugging.json \
		--allow-docker-host-access --debug

bundle-uninstall:
	$(call target_title, "Uninstalling ${DIR} with Porter") \
	&& ${CURRENT_DIR}/devops/scripts/check_dependencies.sh porter \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter uninstall -p ./parameters.json \
		--cred ${CURRENT_DIR}/resource_processor/vmss_porter/arm_auth_local_debugging.json \
		--cred ${CURRENT_DIR}/resource_processor/vmss_porter/aad_auth_local_debugging.json \
		--allow-docker-host-access --debug

bundle-custom-action:
	$(call target_title, "Performing:${ACTION} ${DIR} with Porter") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh porter \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR} && porter invoke --action ${ACTION} -p ./parameters.json \
		--cred ${CURRENT_DIR}/resource_processor/vmss_porter/arm_auth_local_debugging.json \
		--cred ${CURRENT_DIR}/resource_processor/vmss_porter/aad_auth_local_debugging.json \
		--allow-docker-host-access --debug

bundle-publish:
	$(call target_title, "Publishing ${DIR} bundle with Porter") \
	&& ${CURRENT_DIR}/devops/scripts/check_dependencies.sh porter \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/set_docker_sock_permission.sh \
	&& az acr login --name $${ACR_NAME}	\
	&& cd ${DIR} \
	&& porter publish --registry "$${ACR_NAME}.azurecr.io" --debug

bundle-register:
	@# NOTE: ACR_NAME below comes from the env files, so needs the double '$$'. Others are set on command execution and don't
	$(call target_title, "Registering ${DIR} bundle") \
	&& ${CURRENT_DIR}/devops/scripts/check_dependencies.sh porter \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& az acr login --name $${ACR_NAME}	\
	&& . ${CURRENT_DIR}/devops/scripts/get_access_token.sh \
	&& cd ${DIR} \
	&& ${CURRENT_DIR}/devops/scripts/register_bundle_with_api.sh --acr-name "$${ACR_NAME}" --bundle-type "$${BUNDLE_TYPE}" --current --insecure --tre_url "$${TRE_URL:-https://$${TRE_ID}.$${LOCATION}.cloudapp.azure.com}" --verify --workspace-service-name "$${WORKSPACE_SERVICE_NAME}"

deploy-shared-service:
	@# NOTE: ACR_NAME below comes from the env files, so needs the double '$$'. Others are set on command execution and don't
	$(call target_title, "Deploying ${DIR} shared service") \
	&& ${CURRENT_DIR}/devops/scripts/check_dependencies.sh porter \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/get_access_token.sh \
	&& cd ${DIR} \
	&& ${CURRENT_DIR}/devops/scripts/deploy_shared_service.sh --insecure --tre_url "$${TRE_URL:-https://$${TRE_ID}.$${LOCATION}.cloudapp.azure.com}"

static-web-upload:
	$(call target_title, "Uploading to static website") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_terraform_env.sh ./templates/core/.env \
	&& pushd ${CURRENT_DIR}/templates/core/terraform/ > /dev/null && . ${CURRENT_DIR}/outputs.sh && popd > /dev/null \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ${CURRENT_DIR}/templates/core/private.env \
	&& ${CURRENT_DIR}/templates/core/terraform/scripts/upload_static_web.sh

test-e2e-smoke:
	$(call target_title, "Running E2E smoke tests") && \
	cd e2e_tests && \
	python -m pytest -m smoke --verify $${IS_API_SECURED:-true} --junit-xml pytest_e2e_smoke.xml

test-e2e-extended:
	$(call target_title, "Running E2E extended tests") && \
	cd e2e_tests && \
	python -m pytest -m extended --verify $${IS_API_SECURED:-true} --junit-xml pytest_e2e_extended.xml

setup-local-debugging:
	$(call target_title,"Setting up the ability to debug the API and Resource Processor") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& pushd ${CURRENT_DIR}/templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/private.env \
	&& . ${CURRENT_DIR}/scripts/setup_local_debugging.sh

auth:
	$(call target_title,"Setting up Azure Active Directory") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/scripts/create_aad_assets.sh

show-core-output:
	$(call target_title,"Display TRE core output") \
	&& pushd ${CURRENT_DIR}/templates/core/terraform/ > /dev/null && terraform show && popd > /dev/null

api-healthcheck:
	$(call target_title,"Checking API Health") \
	&& . ${CURRENT_DIR}/devops/scripts/check_dependencies.sh nodocker \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./devops/.env \
	&& . ${CURRENT_DIR}/devops/scripts/load_env.sh ./templates/core/private.env \
	&& ${CURRENT_DIR}/devops/scripts/api_healthcheck.sh

db-migrate:
	$(call target_title,"Migrating Cosmos Data") \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& pushd ./templates/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ./devops/scripts/load_env.sh ./templates/core/private.env \
	&& python ./scripts/db_migrations.py
