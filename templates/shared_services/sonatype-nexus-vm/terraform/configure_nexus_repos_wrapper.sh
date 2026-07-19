#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

config_dir="/etc/nexus-data/scripts/nexus_repos_config"
mkdir -p "$config_dir"

%{ for filename, content in REPO_CONFIG_FILES ~}
base64 -d > "$config_dir/${filename}" <<'NEXUS_TRE_EOF'
${content}
NEXUS_TRE_EOF
%{ endfor ~}

base64 -d > /etc/nexus-data/scripts/nexus_realms_config.json <<'NEXUS_TRE_EOF'
${REALMS_CONFIG}
NEXUS_TRE_EOF

base64 -d > /etc/nexus-data/scripts/configure_nexus_repos.sh <<'NEXUS_TRE_EOF'
${CONFIGURE_SCRIPT}
NEXUS_TRE_EOF
chmod 0744 /etc/nexus-data/scripts/configure_nexus_repos.sh

# custom_data is ignored on upgrade, so (re)deploy the container here to apply
# image tag changes to the running VM.
base64 -d > /etc/nexus-data/scripts/deploy_nexus_container.sh <<'NEXUS_TRE_EOF'
${DEPLOY_SCRIPT}
NEXUS_TRE_EOF
chmod 0744 /etc/nexus-data/scripts/deploy_nexus_container.sh
bash /etc/nexus-data/scripts/deploy_nexus_container.sh '${ACR_NAME}' '${NEXUS_IMAGE_TAG}' '${MSI_ID}'

bash /etc/nexus-data/scripts/configure_nexus_repos.sh '${NEXUS_ADMIN_PASSWORD}'
