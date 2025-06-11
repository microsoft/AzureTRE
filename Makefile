.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build-api-image push-api-image tre-deploy tre-destroy letsencrypt
.DEFAULT_GOAL := help

SHELL:=/bin/bash
MAKEFILE_FULLPATH := $(abspath $(lastword $(MAKEFILE_LIST)))
MAKEFILE_DIR := $(dir $(MAKEFILE_FULLPATH))
IMAGE_NAME_PREFIX?="microsoft/azuretre"
ACR_DOMAIN_SUFFIX?=`az cloud show --query suffixes.acrLoginServerEndpoint --output tsv`
ACR_NAME?=`echo "$${ACR_NAME}" | tr A-Z a-z`
ACR_FQDN?="${ACR_NAME}${ACR_DOMAIN_SUFFIX}"
FULL_IMAGE_NAME_PREFIX:=${ACR_FQDN}/${IMAGE_NAME_PREFIX}
LINTER_REGEX_INCLUDE?=all # regular expression used to specify which files to include in local linting (defaults to "all")
E2E_TESTS_NUMBER_PROCESSES_DEFAULT=4  # can be overridden in e2e_tests/.env

target_title = @echo -e "\n\e[34m»»» 🧩 \e[96m$(1)\e[0m..."

# Description: Provision all the application resources from beginning to end
# Example: make all
all: bootstrap mgmt-deploy images tre-deploy ## 🚀 Provision all the application resources from beginning to end

# Description: This command will reuse existing management resource group and the images to provision TRE.
# Example: make tre-deploy
tre-deploy: deploy-core build-and-deploy-ui firewall-install db-migrate show-core-output ## 🚀 Provision TRE using existing images

# Description: Build and push images for API, resource processor and airlock processor.
# Example: make images
images: build-and-push-api build-and-push-resource-processor build-and-push-airlock-processor ## 📦 Build and push all images

# Description: Build and push API image
# Example: make build-and-push-api
build-and-push-api: build-api-image push-api-image

# Description: Build and push Resource Processor image
# Example: make build-and-push-resource-processor
build-and-push-resource-processor: build-resource-processor-vm-porter-image push-resource-processor-vm-porter-image

# Description: Build and push Airlock Processor image
# Example: make build-and-push-airlock-processor
build-and-push-airlock-processor: build-airlock-processor push-airlock-processor

# Description: Display help message on the existing make commands.
# Example: make help
help: ## 💬 This help message :)
	@grep -E '[a-zA-Z_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# Description: Bootstrap Terraform
# Example: make bootstrap
bootstrap:
	$(call target_title, "Bootstrap Terraform") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& cd ${MAKEFILE_DIR}/devops/terraform && ./bootstrap.sh

# Description: Deploy management infrastructure. This will create the management resource group (named <mgmt_resource_group_name> from the config.yaml file) with the necessary resources such as Azure Container Registry, Storage Account for the tfstate and KV for Encryption Keys if enabled.
# Example: make mgmt-deploy
mgmt-deploy:
	$(call target_title, "Deploying management infrastructure") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& cd ${MAKEFILE_DIR}/devops/terraform && ./deploy.sh

# Description: Destroy management infrastructure. This will destroy the management resource group with the resources in it.
# Example: make mgmt-destroy
mgmt-destroy:
	$(call target_title, "Destroying management infrastructure") \
	. ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& cd ${MAKEFILE_DIR}/devops/terraform && ./destroy.sh

# A recipe for building images. Parameters:
# 1. Image name suffix
# 2. Version file path
# 3. Docker file path
# 4. Docker context path
# Example: $(call build_image,"api","./api_app/_version.py","api_app/Dockerfile","./api_app/")
# The CI_CACHE_ACR_NAME is an optional container registry used for caching in addition to what's in ACR_NAME
define build_image
$(call target_title, "Building $(1) Image") \
&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
&& . ${MAKEFILE_DIR}/devops/scripts/set_docker_sock_permission.sh \
&& if [ "$${DISABLE_ACR_PUBLIC_ACCESS}" = "true" ]; then source ${MAKEFILE_DIR}/devops/scripts/mgmtacr_enable_public_access.sh; fi \
&& source <(grep = $(2) | sed 's/ *= */=/g') \
&& az acr login -n ${ACR_NAME} \
&& if [ -n "$${CI_CACHE_ACR_NAME:-}" ]; then \
	az acr login -n $${CI_CACHE_ACR_NAME}; \
	ci_cache="--cache-from $${CI_CACHE_ACR_NAME}${ACR_DOMAIN_SUFFIX}/${IMAGE_NAME_PREFIX}/$(1):$${__version__}"; fi \
&& docker build -t ${FULL_IMAGE_NAME_PREFIX}/$(1):$${__version__} --build-arg BUILDKIT_INLINE_CACHE=1 \
	--cache-from ${FULL_IMAGE_NAME_PREFIX}/$(1):$${__version__} $${ci_cache:-} -f $(3) $(4)
endef

# Description: Build API image using the build_image method.
# Example: make build-api-image
build-api-image:
	$(call build_image,"api","${MAKEFILE_DIR}/api_app/_version.py","${MAKEFILE_DIR}/api_app/Dockerfile","${MAKEFILE_DIR}/api_app/")

# Description: Build Resource Processor VM Porter image using the build_image method.
# Example: make build-resource-processor-vm-porter-image
build-resource-processor-vm-porter-image:
	$(call build_image,"resource-processor-vm-porter","${MAKEFILE_DIR}/resource_processor/_version.py","${MAKEFILE_DIR}/resource_processor/vmss_porter/Dockerfile","${MAKEFILE_DIR}/resource_processor/")

# Description: Build Airlock Processor image using the build_image method.
# Example: make build-airlock-processor
build-airlock-processor:
	$(call build_image,"airlock-processor","${MAKEFILE_DIR}/airlock_processor/_version.py","${MAKEFILE_DIR}/airlock_processor/Dockerfile","${MAKEFILE_DIR}/airlock_processor/")

# A recipe for pushing images. Parameters:
# 1. Image name suffix
# 2. Version file path
# Example: $(call push_image,"api","./api_app/_version.py")
define push_image
$(call target_title, "Pushing $(1) Image") \
&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
&& . ${MAKEFILE_DIR}/devops/scripts/set_docker_sock_permission.sh \
&& if [ "$${DISABLE_ACR_PUBLIC_ACCESS}" = "true" ]; then source ${MAKEFILE_DIR}/devops/scripts/mgmtacr_enable_public_access.sh; fi \
&& source <(grep = $(2) | sed 's/ *= */=/g') \
&& az acr login -n ${ACR_NAME} \
&& docker push "${FULL_IMAGE_NAME_PREFIX}/$(1):$${__version__}"
endef

# Description: Push API image to ACR using the push_image method.
# Example: make push-api-image
push-api-image:
	$(call push_image,"api","${MAKEFILE_DIR}/api_app/_version.py")

# Description: Push Resource Processor VM Porter image to ACR using the push_image method.
# Example: make push-resource-processor-vm-porter-image
push-resource-processor-vm-porter-image:
	$(call push_image,"resource-processor-vm-porter","${MAKEFILE_DIR}/resource_processor/_version.py")

# Description: Push Airlock Processor image to ACR using the push_image method.
# Example: make push-airlock-processor
push-airlock-processor:
	$(call push_image,"airlock-processor","${MAKEFILE_DIR}/airlock_processor/_version.py")

# Description: Deploy the core infrastructure of TRE.
# This will create the core resource group (named rg-<TRE_ID>) with the necessary resources.
# Example: make deploy-core
deploy-core: tre-start
	$(call target_title, "Deploying TRE") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& rm -fr ~/.config/tre/environment.json \
	&& if [[ "$${TF_LOG}" == "DEBUG" ]]; \
		then echo "TF DEBUG set - output supressed - see tflogs container for log file" && cd ${MAKEFILE_DIR}/core/terraform/ \
			&& ./deploy.sh 1>/dev/null 2>/dev/null; \
		else cd ${MAKEFILE_DIR}/core/terraform/ && ./deploy.sh; fi;

# Description: Request LetsEncrypt SSL certificate
# Example: make letsencrypt
letsencrypt:
	$(call target_title, "Requesting LetsEncrypt SSL certificate") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,certbot,env \
	&& pushd ${MAKEFILE_DIR}/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${MAKEFILE_DIR}/core/private.env \
	&& ${MAKEFILE_DIR}/core/terraform/scripts/letsencrypt.sh

# Description: Start the TRE Service.
# # This will allocate the Azure Firewall settings with a public IP and start the Azure Application Gateway service,
# # starting billing of both services.
# Example: make tre-start
tre-start: ## ⏩ Start the TRE Service
	$(call target_title, "Starting TRE") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& ${MAKEFILE_DIR}/devops/scripts/control_tre.sh start

# Description: Stop the TRE Service.
# # This will deallocate the Azure Firewall public IP and stop the Azure Application Gateway service, stopping billing of both services.
# Example: make tre-stop
tre-stop: ## ⛔ Stop the TRE Service
	$(call target_title, "Stopping TRE") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& ${MAKEFILE_DIR}/devops/scripts/control_tre.sh stop

# Description: Destroy the TRE Service. This will destroy all the resources of the TRE service, including the Azure Firewall and Application Gateway.
# Example: make tre-destroy
tre-destroy: ## 🧨 Destroy the TRE Service
	$(call target_title, "Destroying TRE") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& if [ "$${DISABLE_ACR_PUBLIC_ACCESS}" = "true" ]; then source ${MAKEFILE_DIR}/devops/scripts/mgmtacr_enable_public_access.sh; fi \
	&& . ${MAKEFILE_DIR}/devops/scripts/destroy_env_no_terraform.sh

# Description: Deploy the Terraform resources in the specified directory.
# Arguments: DIR - the directory of the bundle
# Example: make terraform-deploy DIR="./templates/workspaces/base"
terraform-deploy:
	$(call target_title, "Deploying ${DIR} with Terraform") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_and_validate_env.sh \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${DIR}/.env \
	&& ./devops/scripts/terraform_deploy.sh ${DIR}

# Description: Upgrade the Terraform resources in the specified directory.
# Arguments: DIR - the directory of the bundle
# Example: make terraform-upgrade DIR="./templates/workspaces/base"
terraform-upgrade:
	$(call target_title, "Upgrading ${DIR} with Terraform") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_and_validate_env.sh \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${DIR}/.env \
	&& ./devops/scripts/terraform_upgrade_provider.sh ${DIR}

# Description: Import the Terraform resources in the specified directory.
# Arguments: DIR - the directory of the bundle
# Example: make terraform-import DIR="./templates/workspaces/base"
terraform-import:
	$(call target_title, "Importing ${DIR} with Terraform") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& cd ${DIR}/terraform/ && ./import.sh

# Description: Destroy the Terraform resources in the specified directory.
# Arguments: DIR - the directory of the bundle
# Example: make terraform-destroy DIR="./templates/workspaces/base"
terraform-destroy:
	$(call target_title, "Destroying ${DIR} Service") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_and_validate_env.sh \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${DIR}/.env \
	&& cd ${DIR}/terraform/ && ./destroy.sh

# Description: Lint files. This will validate all files, not only the changed ones as the CI version does.
# Example: make lint
lint: ## 🧹 Lint all files
	$(call target_title, "Linting")
	@terraform fmt -check -recursive -diff
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
		-e VALIDATE_DOCKERFILE_HADOLINT=true \
		-e VALIDATE_TSX=true \
    -e VALIDATE_TYPESCRIPT_ES=true \
		-e FILTER_REGEX_INCLUDE=${LINTER_REGEX_INCLUDE} \
		-v $${LOCAL_WORKSPACE_FOLDER}:/tmp/lint \
		github/super-linter:slim-v5.0.0

# Description: Lint documentation files
# # This will validate all files, not only the changed ones as the CI version does.
# Example: make lint-docs
lint-docs:
	LINTER_REGEX_INCLUDE='./docs/.*\|./mkdocs.yml' $(MAKE) lint

# Description: Build the bundle with Porter.
# # check-params is called at the end since it needs the bundle image,
# # so we build it first and then run the check.
# Arguments: DIR - the directory of the bundle
# Example: make bundle-build DIR="./templates/workspaces/base"
bundle-build:
	$(call target_title, "Building ${DIR} bundle with Porter") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh porter,env \
	&& . ${MAKEFILE_DIR}/devops/scripts/set_docker_sock_permission.sh \
	&& if [ "$${DISABLE_ACR_PUBLIC_ACCESS}" = "true" ]; then source ${MAKEFILE_DIR}/devops/scripts/mgmtacr_enable_public_access.sh; fi \
	&& cd ${DIR} \
	&& if [ -d terraform ]; then terraform -chdir=terraform init -backend=false; terraform -chdir=terraform validate; fi \
	&& FULL_IMAGE_NAME_PREFIX=${FULL_IMAGE_NAME_PREFIX} IMAGE_NAME_PREFIX=${IMAGE_NAME_PREFIX} \
		${MAKEFILE_DIR}/devops/scripts/bundle_runtime_image_build.sh \
	&& ${MAKEFILE_DIR}/devops/scripts/porter_build_bundle.sh \
	  $(MAKE) bundle-check-params

# Description: Install the bundle with Porter.
# Arguments: DIR - the directory of the bundle
# Example: make bundle-install DIR="./templates/workspaces/base"
bundle-install: bundle-check-params
	$(call target_title, "Deploying ${DIR} with Porter") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh porter,env \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_and_validate_env.sh \
	&& cd ${DIR} \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh .env \
	&& porter parameters apply parameters.json \
	&& porter credentials apply ${MAKEFILE_DIR}/resource_processor/vmss_porter/aad_auth_local_debugging.json \
	&& porter credentials apply ${MAKEFILE_DIR}/resource_processor/vmss_porter/arm_auth_local_debugging.json \
	&& . ${MAKEFILE_DIR}/devops/scripts/porter_local_env.sh \
	&& porter install --autobuild-disabled --parameter-set $$(yq ".name" porter.yaml) \
		--credential-set arm_auth \
		--credential-set aad_auth \
		--debug

# Description: Build, publish and register a bundle based on its type
# Arguments: BUNDLE_TYPE - allowed types are: workspace, workspace_service, shared_service, BUNDLE - bundle name, WORKSPACE_SERVICE - in case of a user resource, provide its parent workspace service
# Example: make bundle BUNDLE_TYPE=workspace BUNDLE=base OR make bundle BUNDLE_TYPE=user_Resource BUNDLE=guacamole-azure-linuxvm WORKSPACE_SERVICE=guacamole
bundle:
	case ${BUNDLE_TYPE} in \
		(workspace) $(MAKE) workspace_bundle BUNDLE=${BUNDLE} ;; \
		(workspace_service) $(MAKE) workspace_service_bundle BUNDLE=${BUNDLE} ;; \
		(shared_service) $(MAKE) shared_service_bundle BUNDLE=${BUNDLE} ;; \
		(user_resource) $(MAKE) user_resource_bundle WORKSPACE_SERVICE=${WORKSPACE_SERVICE} BUNDLE=${BUNDLE} ;; \
		(*) echo "Invalid BUNDLE_TYPE: ${BUNDLE_TYPE}"; exit 1 ;; \
	esac

# Description: Validates that the parameters file is synced with the bundle.
# The file is used when installing the bundle from a local machine.
# We remove arm_use_msi on both sides since it shouldn't take effect locally anyway.
# Arguments: DIR - the directory of the bundle
# Example: make bundle-check-params DIR="./templates/workspaces/base"
bundle-check-params:
	$(call target_title, "Checking bundle parameters in ${DIR}") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,porter \
	&& cd ${DIR} \
	&& if [ ! -f "parameters.json" ]; then echo "Error - please create a parameters.json file."; exit 1; fi \
	&& if [ "$$(jq -r '.name' parameters.json)" != "$$(yq eval '.name' porter.yaml)" ]; then echo "Error - ParameterSet name isn't equal to bundle's name."; exit 1; fi \
	&& if ! porter explain --autobuild-disabled > /dev/null; then echo "Error - porter explain issue!"; exit 1; fi \
	&& comm_output=$$(set -o pipefail && comm -3 --output-delimiter=: <(porter explain --autobuild-disabled -ojson | jq -r '.parameters[].name | select (. != "arm_use_msi")' | sort) <(jq -r '.parameters[].name | select(. != "arm_use_msi")' parameters.json | sort)) \
	&& if [ ! -z "$${comm_output}" ]; \
		then echo -e "*** Add to params ***:*** Remove from params ***\n$$comm_output" | column -t -s ":"; exit 1; \
		else echo "parameters.json file up-to-date."; fi

# Description: Uninstall the bundle with Porter.
# Arguments: DIR - the directory of the bundle
# Example: make bundle-uninstall DIR="./templates/workspaces/base"
bundle-uninstall:
	$(call target_title, "Uninstalling ${DIR} with Porter") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh porter,env \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_and_validate_env.sh \
	&& cd ${DIR} \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh .env \
	&& porter parameters apply parameters.json \
	&& porter credentials apply ${MAKEFILE_DIR}/resource_processor/vmss_porter/aad_auth_local_debugging.json \
	&& porter credentials apply ${MAKEFILE_DIR}/resource_processor/vmss_porter/arm_auth_local_debugging.json \
	&& porter uninstall --autobuild-disabled --parameter-set $$(yq ".name" porter.yaml) \
		--credential-set arm_auth \
		--credential-set aad_auth \
		--debug

# Description: Perform a custom action on the bundle with Porter.
# Arguments: 1. DIR - the directory of the bundle 2. ACTION - the action to perform
# Example: make bundle-custom-action DIR="./templates/workspaces/base" ACTION="action"
bundle-custom-action:
 	$(call target_title, "Performing:${ACTION} ${DIR} with Porter") \
 	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh porter,env \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_and_validate_env.sh \
	&& cd ${DIR}
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh .env \
	&& porter parameters apply parameters.json \
	&& porter credentials apply ${MAKEFILE_DIR}/resource_processor/vmss_porter/aad_auth_local_debugging.json \
	&& porter credentials apply ${MAKEFILE_DIR}/resource_processor/vmss_porter/arm_auth_local_debugging.json \
 	&& porter invoke --autobuild-disabled --action ${ACTION} --parameter-set $$(yq ".name" porter.yaml) \
		--credential-set arm_auth \
		--credential-set aad_auth \
		--debug

# Description: Publish the bundle with Porter to ACR.
# Arguments: DIR - the directory of the bundle
# Example: make bundle-publish DIR="./templates/workspaces/base"
bundle-publish:
	$(call target_title, "Publishing ${DIR} bundle with Porter") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh porter,env \
	&& . ${MAKEFILE_DIR}/devops/scripts/set_docker_sock_permission.sh \
	&& if [ "$${DISABLE_ACR_PUBLIC_ACCESS}" = "true" ]; then source ${MAKEFILE_DIR}/devops/scripts/mgmtacr_enable_public_access.sh; fi \
	&& az acr login --name ${ACR_NAME}	\
	&& cd ${DIR} \
	&& FULL_IMAGE_NAME_PREFIX=${FULL_IMAGE_NAME_PREFIX} \
		${MAKEFILE_DIR}/devops/scripts/bundle_runtime_image_push.sh \
	&& porter publish --registry "${ACR_FQDN}" --force

# Description: Register the bundle with the TRE API.
# Arguments: DIR - the directory of the bundle
# Example: make bundle-register DIR="./templates/workspaces/base"
bundle-register:
	$(call target_title, "Registering ${DIR} bundle") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh porter,env \
	&& . ${MAKEFILE_DIR}/devops/scripts/set_docker_sock_permission.sh \
	&& if [ "$${DISABLE_ACR_PUBLIC_ACCESS}" = "true" ]; then source ${MAKEFILE_DIR}/devops/scripts/mgmtacr_enable_public_access.sh; fi \
	&& az acr login --name ${ACR_NAME}	\
	&& ${MAKEFILE_DIR}/devops/scripts/ensure_cli_signed_in.sh $${TRE_URL} \
	&& cd ${DIR} \
	&& ${MAKEFILE_DIR}/devops/scripts/register_bundle_with_api.sh --acr-name "${ACR_NAME}" --bundle-type "$${BUNDLE_TYPE}" \
		--current --verify \
		--workspace-service-name "$${WORKSPACE_SERVICE_NAME}"

# Description: Build, publish and register a workspace bundle.
# Arguments: BUNDLE - the name of the bundle
# Example: make workspace_bundle BUNDLE=base
# Note: the BUNDLE variable is used to specify the name of the bundle. This should be equivalent to the name of the directory of the template in the templates/workspaces directory.
workspace_bundle:
	$(MAKE) bundle-build bundle-publish bundle-register \
	DIR="${MAKEFILE_DIR}/templates/workspaces/${BUNDLE}" BUNDLE_TYPE=workspace

# Description: Build, publish and register a workspace service bundle.
# Arguments: BUNDLE - the name of the bundle
# Example: make workspace_service_bundle BUNDLE=guacamole
# Note: the BUNDLE variable is used to specify the name of the bundle. This should be equivalent to the name of the directory of the template in the templates/workspace_services directory.
workspace_service_bundle:
	$(MAKE) bundle-build bundle-publish bundle-register \
	DIR="${MAKEFILE_DIR}/templates/workspace_services/${BUNDLE}" BUNDLE_TYPE=workspace_service

# Description: Build, publish and register a shared service bundle.
# Arguments: BUNDLE - the name of the bundle
# Example: make shared_service_bundle BUNDLE=gitea
# Note: the BUNDLE variable is used to specify the name of the bundle. This should be equivalent to the name of the directory of the template in the templates/shared_services directory.
shared_service_bundle:
	$(MAKE) bundle-build bundle-publish bundle-register \
	DIR="${MAKEFILE_DIR}/templates/shared_services/${BUNDLE}" BUNDLE_TYPE=shared_service

# Description: Build, publish and register a user resource bundle.
# Arguments: 1. WORKSPACE_SERVICE - the name of the workspace service 2. BUNDLE - the name of the bundle
# Example: make user_resource_bundle WORKSPACE_SERVICE=guacamole BUNDLE=guacamole-azure-windowsvm
# Note: the WORKSPACE_SERVICE variable is used to specify the name of the workspace service. This should be equivalent to the name of the directory of the template in the templates/workspace_services directory.
# And the BUNDLE variable is used to specify the name of the bundle. This should be equivalent to the name of the directory of the template in the templates/workspace_services/${WORKSPACE_SERVICE}/user_resources directory.
user_resource_bundle:
	$(MAKE) bundle-build bundle-publish bundle-register \
	DIR="${MAKEFILE_DIR}/templates/workspace_services/${WORKSPACE_SERVICE}/user_resources/${BUNDLE}" BUNDLE_TYPE=user_resource WORKSPACE_SERVICE_NAME=tre-service-${WORKSPACE_SERVICE}

# Description: Publish and register all bundles.
# Example: make bundle-publish-register-all
bundle-publish-register-all:
	${MAKEFILE_DIR}/devops/scripts/publish_and_register_all_bundles.sh

# Description: Deploy a shared service.
# Arguments: DIR - the directory of the shared service
# Example: make deploy-shared-service DIR="./templates/shared_services/firewall/"
deploy-shared-service:
	$(call target_title, "Deploying ${DIR} shared service") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh porter,env \
	&& ${MAKEFILE_DIR}/devops/scripts/ensure_cli_signed_in.sh $${TRE_URL} \
	&& cd ${DIR} \
	&& ${MAKEFILE_DIR}/devops/scripts/deploy_shared_service.sh $${PROPS}

# Description: Build, publish and register the firewall shared service. And then deploy the firewall shared service.
# Example: make firewall-install
firewall-install:
	. ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& $(MAKE) bundle-build bundle-publish bundle-register deploy-shared-service \
	DIR=${MAKEFILE_DIR}/templates/shared_services/firewall/ BUNDLE_TYPE=shared_service

# Description: Upload the static website to the storage account
# Example: make static-web-upload
static-web-upload:
	$(call target_title, "Uploading to static website") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& pushd ${MAKEFILE_DIR}/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${MAKEFILE_DIR}/core/private.env \
	&& ${MAKEFILE_DIR}/devops/scripts/upload_static_web.sh

# Description: Build and deploy the UI
# Example: make build-and-deploy-ui
build-and-deploy-ui:
	$(call target_title, "Build and deploy UI") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& pushd ${MAKEFILE_DIR}/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${MAKEFILE_DIR}/core/private.env \
	&& if [ "$${DEPLOY_UI}" != "false" ]; then ${MAKEFILE_DIR}/devops/scripts/build_deploy_ui.sh; else echo "UI Deploy skipped as DEPLOY_UI is false"; fi \

# Description: Prepare for E2E tests by building and registering the necessary bundles such as base workspace, guacamole, gitea, guacamole-azure-windowsvm, guacamole-azure-linuxvm
# Example: make prepare-for-e2e
prepare-for-e2e:
	$(MAKE) workspace_bundle BUNDLE=base
	$(MAKE) workspace_service_bundle BUNDLE=guacamole
	$(MAKE) shared_service_bundle BUNDLE=gitea
	$(MAKE) user_resource_bundle WORKSPACE_SERVICE=guacamole BUNDLE=guacamole-azure-windowsvm
	$(MAKE) user_resource_bundle WORKSPACE_SERVICE=guacamole BUNDLE=guacamole-azure-linuxvm

# Description: Run E2E smoke tests
# The E2E smoke tests include:
# - test_get_workspace_templates: GET Request to get all workspace templates
# - test_get_workspace_template: GET Request to get a specific workspace template: base
# - test_get_workspace_service_templates: GET Request to get all workspace service templates
# - test_get_workspace_service_template: GET Request to get a specific workspace service template for example: guacamole
# - test_get_shared_service_templates:	GET Request to get all shared service templates
# - test_get_shared_service_template: GET Request to get a specific shared service template for example: gitea
test-e2e-smoke:	## 🧪 Run E2E smoke tests
	$(call target_title, "Running E2E smoke tests") && \
	$(MAKE) test-e2e-custom SELECTOR=smoke

# Description: Run E2E extended tests
# # The E2E extended tests include:
# # - test_create_workspace_templates: POST Request to create a workspace template
# # - test_create_guacamole_service_into_base_workspace: POST Request to create a workspace and a separate POST call to create a guacamole workspace service into the base workspace
# # - test_airlock_flow: test import and export flow
# Example: make test-e2e-extended
test-e2e-extended: ## 🧪 Run E2E extended tests
	$(call target_title, "Running E2E extended tests") && \
	$(MAKE) test-e2e-custom SELECTOR=extended

# Description: Run E2E extended AAD tests
# # The E2E extended AAD tests include:
# # - test_create_guacamole_service_into_aad_workspace: This test will create a Guacamole service but will create a workspace and automatically register the AAD Application
# Example: make test-e2e-extended-aad
test-e2e-extended-aad: ## 🧪 Run E2E extended AAD tests
	$(call target_title, "Running E2E extended AAD tests") && \
	$(MAKE) test-e2e-custom SELECTOR=extended_aad

# Description: Run E2E shared service tests
# # The E2E shared service tests include:
# # - test_patch_firewall: verifies the ability to update the firewall shared service with new rule collections by sending a PATCH request to the appropriate API endpoint.
# # - test_create_certs_nexus_shared_service: verifies the creation and subsequent deletion of the Nexus shared service with SSL certificates by deploying both the Certs and Nexus shared services and ensuring they are properly configured and removed.
# # - test_create_shared_service: verifies the creation and subsequent deletion of various shared services by deploying them via API requests and ensuring they are properly configured and removed.
# Example: make test-e2e-shared-services
test-e2e-shared-services: ## 🧪 Run E2E shared service tests
	$(call target_title, "Running E2E shared service tests") && \
	$(MAKE) test-e2e-custom SELECTOR=shared_services

# Description: Run E2E tests with custom selector
# Arguments: SELECTOR - the selector to run the tests with
# Example: make test-e2e-custom SELECTOR=smoke
test-e2e-custom: ## 🧪 Run E2E tests with custom selector (SELECTOR=)
	$(call target_title, "Running E2E tests with custom selector ${SELECTOR}") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env,auth \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${MAKEFILE_DIR}/e2e_tests/.env \
	&& cd ${MAKEFILE_DIR}/e2e_tests \
	&& \
		if [[ -n "$${E2E_TESTS_NUMBER_PROCESSES}" && "$${E2E_TESTS_NUMBER_PROCESSES}" -ne 1 ]]; then \
			python -m pytest -n "$${E2E_TESTS_NUMBER_PROCESSES}" -m "${SELECTOR}" --verify $${IS_API_SECURED:-true} --junit-xml "pytest_e2e_$${SELECTOR// /_}.xml"; \
		elif [[ "$${E2E_TESTS_NUMBER_PROCESSES}" -eq 1 ]]; then \
			python -m pytest -m "${SELECTOR}" --verify $${IS_API_SECURED:-true} --junit-xml "pytest_e2e_$${SELECTOR// /_}.xml"; \
		else \
			python -m pytest -n "${E2E_TESTS_NUMBER_PROCESSES_DEFAULT}" -m "${SELECTOR}" --verify $${IS_API_SECURED:-true} --junit-xml "pytest_e2e_$${SELECTOR// /_}.xml"; fi

# Description: Setup the ability to debug the API and Resource Processor by  configuring settings and permissions required for debugging.
# Example: make setup-local-debugging
setup-local-debugging: ## 🛠️ Setup local debugging
	$(call target_title,"Setting up the ability to debug the API and Resource Processor") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& pushd ${MAKEFILE_DIR}/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${MAKEFILE_DIR}/core/private.env \
	&& . ${MAKEFILE_DIR}/devops/scripts/setup_local_debugging.sh

# Description: Create the necessary Azure Active Directory assets for TRE.
# Example: make auth
auth: ## 🔐 Create the necessary Azure Active Directory assets
	$(call target_title,"Setting up Azure Active Directory") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& ${MAKEFILE_DIR}/devops/scripts/create_aad_assets.sh

# Description: Display TRE core output
# Example: make show-core-output
show-core-output:
	$(call target_title,"Display TRE core output") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh env \
	&& pushd ${MAKEFILE_DIR}/core/terraform/ > /dev/null && . ./show_output.sh && popd > /dev/null

# Description: Check the API health
# Example: make api-healthcheck
api-healthcheck:
	$(call target_title,"Checking API Health") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${MAKEFILE_DIR}/core/private.env \
	&& ${MAKEFILE_DIR}/devops/scripts/api_healthcheck.sh

# Description: Run database migrations
# Example: make db-migrate
db-migrate: api-healthcheck ## 🗄️ Run database migrations
	$(call target_title,"Migrating Cosmos Data") \
	&& . ${MAKEFILE_DIR}/devops/scripts/check_dependencies.sh nodocker,env \
	&& pushd ${MAKEFILE_DIR}/core/terraform/ > /dev/null && . ./outputs.sh && popd > /dev/null \
	&& . ${MAKEFILE_DIR}/devops/scripts/load_env.sh ${MAKEFILE_DIR}/core/private.env \
	&& . ${MAKEFILE_DIR}/devops/scripts/get_access_token.sh \
	&& . ${MAKEFILE_DIR}/devops/scripts/migrate_state_store.sh --tre_url $${TRE_URL} --insecure
