#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

if [ "$#" -eq 0 ]; then
  echo "Usage: dockerfile_build_retry.sh command [arguments...]" >&2
  exit 2
fi

for attempt in 1 2; do
  echo "::group::Build attempt ${attempt}/2"
  if "$@"; then
    echo "::endgroup::"
    exit 0
  else
    result=$?
  fi
  echo "::endgroup::"

  # A cancelled command must not start another build.
  case "$result" in
    130|143) exit "$result" ;;
  esac

  if [ "$attempt" -eq 1 ]; then
    echo "::warning::Build attempt 1 failed with exit code ${result}. Retrying in 10 seconds."
    sleep 10
  fi
done

echo "::error::Both build attempts failed. Last exit code: ${result}." >&2
exit "$result"
