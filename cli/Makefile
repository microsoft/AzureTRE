PHONY: pip-install install-cli build-package

help: ## show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%s\033[0m|%s\n", $$1, $$2}' \
	| column -t -s '|'

pip-install: ## install required dependencides
	pip install -r requirements.txt

install-cli: ## install CLI (note, run `source <(_TRE_COMPLETE=bash_source tre)` to set up bash completion)
	sudo rm -rf build dist tre.egg-info
	sudo pip install .

build-package: ## build package
	./scripts/build.sh

