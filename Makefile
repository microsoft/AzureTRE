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
	&& cd ./workspaces/vanilla/ && porter build

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
	&& ./devops/scripts/publish_vanilla_workspace.sh




