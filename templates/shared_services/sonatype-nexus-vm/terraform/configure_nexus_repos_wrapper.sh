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

bash /etc/nexus-data/scripts/configure_nexus_repos.sh '${NEXUS_ADMIN_PASSWORD}'
