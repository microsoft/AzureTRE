#!/bin/bash

ACR_NAME="${1:-}"
NEXUS_IMAGE_TAG="${2:-latest}"
MSI_CLIENT_ID="${3:-}"

# Determine which image to pull
if [ -n "$ACR_NAME" ]; then
  NEXUS_IMAGE="${ACR_NAME}.azurecr.io/sonatype/nexus3:${NEXUS_IMAGE_TAG}"
  ACR_LOGIN_SERVER="${ACR_NAME}.azurecr.io"
  echo "Pulling Nexus image from ACR: $NEXUS_IMAGE"

  # Login to ACR using managed identity via IMDS (bypasses firewall, uses private endpoint)
  if [ -n "$MSI_CLIENT_ID" ]; then
    echo "Logging in to ACR using managed identity via IMDS..."
    # Get AAD token using IMDS - HTTP to link-local address bypasses firewall
    ACCESS_TOKEN=$(curl -s -H 'Metadata:true' "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&client_id=${MSI_CLIENT_ID}&resource=https://management.azure.com/" | jq -r '.access_token')
    if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
      echo "ERROR - Failed to get access token from IMDS"
      exit 1
    fi
    # Exchange AAD token for ACR refresh token (via private endpoint)
    ACR_REFRESH_TOKEN=$(curl -s -X POST "https://${ACR_LOGIN_SERVER}/oauth2/exchange" -H "Content-Type: application/x-www-form-urlencoded" -d "grant_type=access_token&service=${ACR_LOGIN_SERVER}&access_token=${ACCESS_TOKEN}" | jq -r '.refresh_token')
    if [ -z "$ACR_REFRESH_TOKEN" ] || [ "$ACR_REFRESH_TOKEN" == "null" ]; then
      echo "ERROR - Failed to get ACR refresh token"
      exit 1
    fi
    # Login to Docker with ACR refresh token
    if ! echo "${ACR_REFRESH_TOKEN}" | docker login "${ACR_LOGIN_SERVER}" --username 00000000-0000-0000-0000-000000000000 --password-stdin; then
      echo "ERROR - Docker login to ACR failed"
      exit 1
    fi
    echo "Successfully logged in to ACR"
  fi
else
  NEXUS_IMAGE="sonatype/nexus3:${NEXUS_IMAGE_TAG}"
  echo "Pulling Nexus image from Docker Hub: $NEXUS_IMAGE"
fi

docker_pull_timeout=10

while true; do
  if [ $docker_pull_timeout == 0 ]; then
    echo "ERROR - Timeout while waiting for $NEXUS_IMAGE to be pulled"
    exit 1
  fi

  if docker pull "$NEXUS_IMAGE"; then
      echo "Image pulled successfully"
      break
  else
      echo "Failed to pull image, restarting Docker service"
      systemctl restart docker.service
      sleep 60
  fi

  ((docker_pull_timeout--));
done

# Deduce memory available to Java. Either 3/4 of the system RAM, or a set minimum
# shellcheck disable=SC2002
mem_total_mb=$(( $(cat /proc/meminfo | head -1 | awk '{ print $2 }') / 1024 ))
java_mem=2703
if [ $mem_total_mb -gt 4096 ]; then
  java_mem=$(( mem_total_mb * 3 / 4 ))
fi

echo "System memory: ${mem_total_mb} MB. Java memory: ${java_mem} MB"

docker run -d -p 80:8081 -p 443:8443 -p 8083:8083 -v /etc/nexus-data:/nexus-data \
    -e INSTALL4J_ADD_VM_PARAMS="-Xmx${java_mem}m -Xms${java_mem}m" \
    --restart always \
    --name nexus \
    --log-driver local \
    "$NEXUS_IMAGE"
