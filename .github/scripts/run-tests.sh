#!/bin/bash
set -o errexit
set -o pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

function usage() {
    cat <<USAGE

    This script runs the GitHub action linter and unit tests for build.js
    Dependencies (e.g. node, actionlint) will be installed if not present

    Usage: $0 [--watch]

    Options:
        --watch   Run tests in watch mode
USAGE
    exit 1
}


watch_tests=false
while [ "$1" != "" ]; do
    case $1 in
    --watch)
        watch_tests=true
        ;;
    *)
        echo "Unexpected argument: '$1'"
        usage
        ;;
    esac

    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi

    shift # remove the current value for `$1` and use the next
done
test_command="test"
if ${watch_tests}
then
  test_command="test-watch"
fi


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


if [[ $(command -v node > /dev/null; echo $?) == 0 ]]; then
  echo "node already installed"
else
  echo "node not found - installing..."
  "$DIR/install-node.sh"
fi

echo "Running JavaScript build tests..."
(cd "$DIR" && yarn install && yarn "$test_command")

echo "Tests complete"
