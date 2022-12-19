#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

export PORTER_HOME=${PORTER_HOME:-~/.porter}
export PORTER_MIRROR=${PORTER_MIRROR:-https://cdn.porter.sh}
PORTER_VERSION=${PORTER_VERSION:-latest}

echo "Installing porter@$PORTER_VERSION to $PORTER_HOME from $PORTER_MIRROR"

mkdir -p "$PORTER_HOME/runtimes"

curl -fsSLo "$PORTER_HOME/porter" "$PORTER_MIRROR/$PORTER_VERSION/porter-linux-amd64"
chmod +x "$PORTER_HOME/porter"
ln -s "$PORTER_HOME/porter" "$PORTER_HOME/runtimes/porter-runtime"
echo "Installed $("${PORTER_HOME}"/porter version)"

"${PORTER_HOME}/porter" mixin install exec --version "$PORTER_VERSION"
"${PORTER_HOME}/porter" mixin install terraform --version "$PORTER_TERRAFORM_MIXIN_VERSION"
"${PORTER_HOME}/porter" mixin install az --version "$PORTER_AZ_MIXIN_VERSION"

"${PORTER_HOME}/porter" plugin install azure --version "$PORTER_AZURE_PLUGIN_VERSION"

chown -R "${USERNAME}" "${PORTER_HOME}"

echo "Installation complete."
