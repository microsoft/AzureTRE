#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

mkdir -p "${PORTER_HOME}/runtimes"
curl -fsSLo "${PORTER_HOME}/porter" "${PORTER_MIRROR}/${PORTER_VERSION}/porter-linux-amd64"
chmod +x "${PORTER_HOME}/porter"
ln -s "${PORTER_HOME}/porter" "${PORTER_HOME}/runtimes/porter-runtime"

"${PORTER_HOME}/porter" mixin install exec --version "${PORTER_VERSION}"
"${PORTER_HOME}/porter" mixin install terraform --version "${PORTER_TERRAFORM_MIXIN_VERSION}"
"${PORTER_HOME}/porter" mixin install az --version "${PORTER_AZ_MIXIN_VERSION}"
"${PORTER_HOME}/porter" plugin install azure --version "${PORTER_AZURE_PLUGIN_VERSION}"
