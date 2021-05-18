.PHONY: bootstrap-init mgmt-deploy mgmt-destroy build_images push_images deploy-tre destroy-tre

SHELL:=/bin/bash

all: bootstrap-init mgmt-deploy build_images push_images deploy-tre

bootstrap:
	echo -e "\n\e[34m»»» 🧩 \e[Bootstrap Terraform\e[0m..." \
	&& . ./devops/scripts/check_dependancies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform && ./bootstrap.sh

mgmt-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying management infrastructure\e[0m..." \
	&& . ./devops/scripts/check_dependancies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform  &&  ./deploy.sh  

mgmt-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[Destroying management infrastructure\e[0m..." \
	. ./devops/scripts/check_dependancies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& cd ./devops/terraform  && ./destroy.sh

build-images:
	echo -e "\n\e[34m»»» 🧩 \e[Building Images\e[0m..." \
	&& . ./devops/scripts/check_dependancies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/build_images.sh

push-images:
	echo -e "\n\e[34m»»» 🧩 \e[Pushing Images\e[0m..." \
	. ./devops/scripts/check_dependancies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& ./devops/scripts/push_images.sh

tre-deploy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDeploying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependancies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& cd ./templates/core/terraform/ && ./deploy.sh 

tre-destroy:
	echo -e "\n\e[34m»»» 🧩 \e[96mDestroying TRE\e[0m..." \
	&& . ./devops/scripts/check_dependancies.sh \
	&& . ./devops/scripts/load_env.sh ./devops/terraform/.env \
	&& . ./devops/scripts/load_env.sh ./templates/core/terraform/.env \
	&& cd ./templates/core/terraform/ && ./destroy.sh 