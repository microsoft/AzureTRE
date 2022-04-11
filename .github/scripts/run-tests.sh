#!/bin/bash
set -e


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [[ $(command -v node > /dev/null; echo $?) == 0 ]]; then
  echo "node already installed"
else
  echo "node not found - installing..."
  "$DIR/install-node.sh"
fi

(cd "$DIR" && yarn test)
