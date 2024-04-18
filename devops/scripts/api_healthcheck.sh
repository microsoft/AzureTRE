#!/bin/bash
# This script checks if the api server endpoint /api/health is available(response code 200) and then verifies that the response contains all OK
# Both verifications have a retry(4 retries, including call above makes total 5 calls).
set -e

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Create a .gitignore'd  directory for temp output
mkdir -p "$DIR/script_tmp"
echo '*' > "$DIR/script_tmp/.gitignore"

function call_and_parse() {
  response_code=$($command)
  if [[ $1 = true ]]; then
    response_code=$(jq '.services| .[] | select(.status!="OK") | length' "$api_response_file")
  fi
}

function call_with_retry() {
  retries_left=6

  echo "$command"
  call_and_parse "$2"

  while [[ "${response_code}" -ne $1 ]] && [[ $retries_left -gt 0 ]]; do
    printf "running %s -- %d retries left\n" "$command" "$retries_left"
    call_and_parse "$2"

    sleep_time=$((30*retries_left))
    echo "Sleeping for $sleep_time secs before trying again..."
    sleep $sleep_time

    retries_left=$(( retries_left - 1))
  done

  if [[ retries_left -eq 0 ]]; then
    call_ok=false
  else
    call_ok=true
  fi
}

api_response_file="$DIR/script_tmp/api_response.txt"
command="curl --insecure --silent --output $api_response_file --write-out %{http_code} ${TRE_URL}/api/health"
call_with_retry "200" false

if [[ $call_ok = true ]]; then
  command="curl --insecure --silent --output $api_response_file ${TRE_URL}/api/health"
  call_with_retry "" true
fi

if [[ $call_ok = false ]]; then
  echo "*** ⚠️ API _not_ healthy ***"
  echo "Response:"
  cat "$api_response_file"
  exit 1
fi

cat "$api_response_file"
printf "\n*** ✅ API healthy ***\n"
