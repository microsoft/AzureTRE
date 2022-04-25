#!/bin/bash
set -e


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [[ $(command -v node > /dev/null; echo $?) == 0 ]]; then
  echo "node already installed"
else
  echo "node not found - installing..."
  "$DIR/install-node.sh"
fi

echo "Running JavaScript build tests..."
(cd "$DIR" && yarn test)

script_temp_dir="$DIR/script_temp"
if [[ -x "$script_temp_dir/actionlint" ]]; then
  echo "actionlint already installed"
  "$script_temp_dir/actionlint" -version
else
  echo "actionlint not found - installing..."
  mkdir -p "$script_temp_dir"
  echo '*' > "$script_temp_dir/.gitignore"
  (cd "$script_temp_dir" && bash <(curl https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash))
fi
echo "Running actionlint..."
"$script_temp_dir/actionlint"
echo "Tests complete"
