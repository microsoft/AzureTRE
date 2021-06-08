.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build-api-image push-api-image build-cnab-image push-cnab-image deploy-tre destroy-tre letsencrypt

SHELL:=/bin/bash

all: bootstrap mgmt-deploy build-api-image push-api-image build-cnab-image push-cnab-image tre-deploy

bootstrap:
	echo -e "\n\e[34m»»» 🧩 \e[96mBootstrap Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform && ./bootstrap.sh

mgmt-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying management infrastructure\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform && ./deploy.sh

mgmt-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying management infrastructure\e[0m..." \
	. ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform && ./destroy.sh

build-api-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/build_images.sh api

build-cnab-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/build_images.sh cnab

push-api-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/push_images.sh api

push-cnab-image:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/push_images.sh cnab

tre-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& cd ./templates/core/terraform/ && ./deploy.sh

letsencrypt:
	echo -e "\n\e[34m»»» 🧩 \e[96mRequesting LetsEncrypt SSL certificate\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker,certbot \
	&& chmod 755 ./devops/scripts/letsencrypt.sh ./devops/scripts/auth-hook.sh ./devops/scripts/cleanup-hook.sh \
	&& . ./devops/scripts/get-coreenv.sh \
	&& ./devops/scripts/letsencrypt.sh

tre-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& cd ./templates/core/terraform/ && ./destroy.sh

workspaces-vanilla-tf-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying Base Workspace with Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./workspaces/vanilla/terraform/.env \
	&& cd ./workspaces/vanilla/terraform/ && ./deploy.sh

workspaces-vanilla-tf-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying Base Workspace\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./workspaces/vanilla/terraform/.env \
	&& cd ./workspaces/vanilla/terraform/ && ./destroy.sh 

workspaces-vanilla-porter-build:
	echo -e "\n\e[34m»»» 🧩 \e[Building vanilla workspace bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& cd ./workspaces/vanilla/ && porter build --debug

workspaces-vanilla-porter-install:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying Base Workspace with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./workspaces/vanilla/.env \
	&& cd ./workspaces/vanilla/ && porter install -p ./parameters.json --cred ./azure.json --debug

workspaces-vanilla-porter-uninstall:
	echo -e "\n\e[34m»»» 🧩 \e[96mUninstalling Base Workspace with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./workspaces/vanilla/.env \
	&& cd ./workspaces/vanilla/ && porter uninstall -p ./parameters.json --cred ./azure.json --debug

workspaces-vanilla-porter-publish:
	echo -e "\n\e[34m»»» 🧩 \e[96mPublishing vanilla workspace bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&&  cd ./workspaces/vanilla/ && ../../devops/scripts/publish_bundle.sh

# Workspace: Azure ML and DevTest Labs
workspaces-azureml_devtestlabs-porter-build:
	echo -e "\n\e[34m»»» 🧩 \e[Building azureml_devtestlabs workspace bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& cd ./workspaces/azureml_devtestlabs/ && porter build --debug

workspaces-azureml_devtestlabs-porter-install:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying azureml_devtestlabs with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./workspaces/azureml_devtestlabs/.env \
	&& cd ./workspaces/azureml_devtestlabs/ && porter install  --allow-docker-host-access --param porter_driver="docker" -p ./parameters.json --cred ./azure.json --debug

workspaces-azureml_devtestlabs-porter-uninstall:
	echo -e "\n\e[34m»»» 🧩 \e[96mUninstalling Base Workspace with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./workspaces/azureml_devtestlabs/.env \
	&& cd ./workspaces/azureml_devtestlabs/ && porter uninstall  --allow-docker-host-access -p ./parameters.json --cred ./azure.json --debug

workspaces-azureml_devtestlabs-porter-publish:
	echo -e "\n\e[34m»»» 🧩 \e[96mPublishing azureml_devtestlabs workspace bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&&  cd ./workspaces/azureml_devtestlabs/ && ../../devops/scripts/publish_bundle.sh

# Service: Azure ML
services-azureml-tf-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying Azure ML Service with Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./workspaces/services/azureml/terraform/.env \
	&& cd ./workspaces/services/azureml/terraform/ && ./deploy.sh

services-azureml-tf-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying Azure ML Service\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./workspaces/services/azureml/terraform/.env \
	&& cd ./workspaces/services/azureml/terraform/ && ./destroy.sh 

services-azureml-porter-build:
	echo -e "\n\e[34m»»» 🧩 \e[Building Azure ML Servicee bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& cd ./workspaces/services/azureml/ && porter build --debug

services-azureml-porter-install:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying Azure ML Service with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./workspaces/services/azureml/.env \
	&& cd ./workspaces/services/azureml/ && porter install -p ./parameters.json --cred ./azure.json --debug

services-azureml-porter-uninstall:
	echo -e "\n\e[34m»»» 🧩 \e[96mUninstalling Azure ML Service with Porter\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./workspaces/services/azureml/.env \
	&& cd ./workspaces/services/azureml/ && porter uninstall -p ./parameters.json --cred ./azure.json --debug

services-azureml-porter-publish:
	echo -e "\n\e[34m»»» 🧩 \e[96mPublishing Azure ML Service bundle\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh porter \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&&  cd ./workspaces/services/azureml/ && ../../../devops/scripts/publish_bundle.sh


