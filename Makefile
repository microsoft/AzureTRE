.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build_images push_images deploy-tre destroy-tre

SHELL:=/bin/bash

all: bootstrap mgmt-deploy build-images push-images tre-deploy

bootstrap:
	echo -e "\n\e[34m»»» 🧩 \e[96mBootstrap Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform && ./bootstrap.sh

mgmt-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying management infrastructure\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform  &&  ./deploy.sh  

mgmt-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying management infrastructure\e[0m..." \
	. ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform  && ./destroy.sh

build-images:
	echo -e "\n\e[34m»»» 🧩 \e[96mBuilding Images\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/build_images.sh

push-images:
	echo -e "\n\e[34m»»» 🧩 \e[96mPushing Images\e[0m..." \
	. ./devops/scripts/check_dependencies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/push_images.sh

tre-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& cd ./templates/core/terraform/ && ./deploy.sh 

tre-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& cd ./templates/core/terraform/ && ./destroy.sh 

base-workspace-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying Base Workspace\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/workspaces/base_workspace/terraform/.env \
	&& cd ./templates/workspaces/base_workspace/terraform/ && ./deploy.sh 

base-workspace-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying Base Workspace\e[0m..." \
	&& . ./devops/scripts/check_dependencies.sh nodocker \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/workspaces/base_workspace/terraform/.env \
	&& cd ./templates/workspaces/base_workspace/terraform/ && ./destroy.sh 