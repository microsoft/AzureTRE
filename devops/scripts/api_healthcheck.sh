#!/bin/bash
# This script checks if the API server endpoint /api/health is available (response code 200)
# and verifies that the response contains all services with OK status.
# Uses fixed intervals between retries with a maximum timeout.
set -e

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Create a .gitignore'd directory for temp output
mkdir -p "$DIR/script_tmp"
echo '*' > "$DIR/script_tmp/.gitignore"

api_response_file="$DIR/script_tmp/api_response.txt"
max_time=420  # 7 minutes in seconds
check_interval=10
elapsed_time=0
attempt=1

# Function to check API health endpoint
check_api_health() {
  local http_code
  # shellcheck disable=SC1083
  http_code=$(curl --insecure --silent --output "$api_response_file" --write-out %{http_code} "${TRE_URL}/api/health")
  echo "$http_code"
}

# Function to parse response for service status
check_all_services_ok() {
  local unhealthy_count
  unhealthy_count=$(jq '.services | .[] | select(.status!="OK") | length' "$api_response_file" 2>/dev/null || echo "0")
  if [[ "$unhealthy_count" -eq 0 ]]; then
    return 0
  else
    return 1
  fi
}

echo "Checking API health at ${TRE_URL}/api/health"
echo "Max timeout: ${max_time} seconds (7 minutes)"
echo "Check interval: ${check_interval} seconds"
echo ""

# Initial health check
http_code=$(check_api_health)
echo "Attempt $attempt: HTTP $http_code (elapsed: ${elapsed_time}s)"

# Keep trying until we get 200 response
while [[ "$http_code" -ne 200 ]] && [[ $elapsed_time -lt $max_time ]]; do
  elapsed_time=$((elapsed_time + check_interval))
  if [[ $elapsed_time -ge $max_time ]]; then
    break
  fi
  echo "Waiting ${check_interval}s before retry..."
  sleep "$check_interval"

  attempt=$((attempt + 1))
  http_code=$(check_api_health)
  echo "Attempt $attempt: HTTP $http_code (elapsed: ${elapsed_time}s / ${max_time}s)"
done

# If we got 200, verify all services are OK
if [[ "$http_code" -eq 200 ]]; then
  while ! check_all_services_ok && [[ $elapsed_time -lt $max_time ]]; do
    echo "Some services are not OK after ${elapsed_time} seconds (${attempt} attempts)"
    echo "Response:"
    cat "$api_response_file"
    elapsed_time=$((elapsed_time + check_interval))
    if [[ $elapsed_time -ge $max_time ]]; then
      break
    fi
    echo "Not all services OK. Waiting ${check_interval}s before retry..."
    sleep "$check_interval"

    attempt=$((attempt + 1))
    http_code=$(check_api_health)
    echo "Attempt $attempt: HTTP $http_code (elapsed: ${elapsed_time}s / ${max_time}s)"
  done
fi

# Check final status
if [[ "$http_code" -ne 200 ]]; then
  echo ""
  echo "*** ⚠️ API _not_ healthy ***"
  echo "Failed to get 200 response after ${elapsed_time} seconds (${attempt} attempts)"
  echo "Response:"
  cat "$api_response_file" 2>/dev/null || echo "(No response captured)"
  exit 1
fi

if ! check_all_services_ok; then
  echo ""
  echo "*** ⚠️ API _not_ healthy ***"
  echo "Some services are not OK after ${elapsed_time} seconds (${attempt} attempts)"
  echo "Response:"
  cat "$api_response_file"
  exit 1
fi

echo ""
cat "$api_response_file"
echo ""
echo "*** ✅ API healthy (${attempt} attempts, ${elapsed_time}s elapsed) ***"
