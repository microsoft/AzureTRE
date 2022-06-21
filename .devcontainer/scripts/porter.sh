#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

mkdir -p "${PORTER_HOME}/runtimes"
curl -fsSLo "${PORTER_HOME}/porter" "${PORTER_MIRROR}/${PORTER_PERMALINK}/porter-linux-amd64"
chmod +x "${PORTER_HOME}/porter"
ln -s "${PORTER_HOME}/porter" "${PORTER_HOME}/runtimes/porter-runtime"

"${PORTER_HOME}/porter" mixin install exec --version "${PORTER_PKG_PERMALINK}"
"${PORTER_HOME}/porter" mixin install terraform --version "${PORTER_PKG_PERMALINK}"
"${PORTER_HOME}/porter" mixin install az --version "${PORTER_PKG_PERMALINK}"
"${PORTER_HOME}/porter" plugin install azure --version "${PORTER_PKG_PERMALINK}"
"${PORTER_HOME}/porter" mixin install docker --version "${PORTER_PKG_PERMALINK}"

chown -R "${USERNAME}" "${PORTER_HOME}"
