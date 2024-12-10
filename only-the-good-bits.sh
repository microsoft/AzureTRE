#!/bin/bash
set -o errexit
set -o pipefail

here=$(pwd)
targets="bundle-build bundle-publish bundle-register"
# targets="bundle-build bundle-publish"
# targets="bundle-build"

# templates/shared_services/certs
# templates/shared_services/firewall
# templates/shared_services/gitea
# templates/shared_services/sonatype-nexus-vm
for bundle in certs gitea sonatype-nexus-vm firewall
do
  # shellcheck disable=SC2086
  make ${targets} \
	  DIR="${here}/templates/shared_services/${bundle}" \
    BUNDLE_TYPE=shared_service
done

# templates/workspaces/base
# shellcheck disable=SC2043
for bundle in base
do
  # shellcheck disable=SC2086
  make ${targets} \
	  DIR="${here}/templates/workspaces/${bundle}" \
    BUNDLE_TYPE=workspace
done

# templates/workspace_services/guacamole
# shellcheck disable=SC2043
for bundle in guacamole
do
  # shellcheck disable=SC2086
  make ${targets} \
    DIR="${here}/templates/workspace_services/${bundle}" \
    BUNDLE_TYPE=workspace_service
done

for bundle in guacamole-azure-linuxvm  guacamole-azure-windowsvm
do
	# shellcheck disable=SC2086
	make ${targets} \
	  DIR="${here}/templates/workspace_services/guacamole/user_resources/${bundle}" \
    BUNDLE_TYPE=user_resource \
    WORKSPACE_SERVICE_NAME=tre-service-guacamole
done

echo "Run ... make bundle-publish-register-all"
