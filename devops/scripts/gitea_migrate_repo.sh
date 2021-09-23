#!/bin/bash
set -e

# These variables need to be set
# ******************************
# TRE_ID=
# LOCATION=

# TENANT_ID=
# SUBSCRIPTION_ID=
# ARM_CLIENT_ID=
# ARM_CLIENT_SECRET=

# ORGANISATION=microsoft
# REPO_NAME=InnerEye-DeepLearning

username=gitea_admin

keyVaultName="kv-"$TRE_ID
tokenSecretName="gitea-"$TRE_ID"-admin-token"
pwdSecretName="gitea-"$TRE_ID"-admin-password"

gitea_url="https://$TRE_ID.$LOCATION.cloudapp.azure.com/gitea"

az login --service-principal --username $ARM_CLIENT_ID --password $ARM_CLIENT_SECRET --tenant $TENANT_ID > /dev/null

# Check if access token exists
token_exists=$(az keyvault secret list --subscription $SUBSCRIPTION_ID --vault-name $keyVaultName --query "contains([].id, 'https://$keyVaultName.vault.azure.net/secrets/$tokenSecretName')")

if $token_exists
then
  response=$(az keyvault secret show --subscription $SUBSCRIPTION_ID --vault-name $keyVaultName --name $tokenSecretName)
  token=$(jq -r '.value' <<< "$response")
else
  # Get admin password from keyvault
  response=$(az keyvault secret show --subscription $SUBSCRIPTION_ID --vault-name $keyVaultName --name $pwdSecretName)
  password=$(jq -r '.value' <<< "$response")

  credentials=$username:$password
  data='{"name": "'${username}'"}'
  url=${gitea_url}/api/v1/users/${username}/tokens

  # Create new access token
  response=$(curl -X POST -H "Content-Type: application/json" -k -d "${data}" -u ${credentials} ${url})
  token=$(jq -r '.sha1' <<< "$response")

  # Store access token to keyvault
  az keyvault secret set --name $tokenSecretName --vault-name $keyVaultName --value $token > /dev/null
fi

# Repository migration parameters
repo='{
  "clone_addr": "https://github.com/'${ORGANISATION}'/'${REPO_NAME}'",
  "issues": true,
  "labels": true,
  "lfs": false,
  "milestones": true,
  "mirror": true,
  "mirror_interval": "12h0m0s",
  "private": true,
  "pull_requests": true,
  "releases": true,
  "repo_name": "'${REPO_NAME}'",
  "service": "github",
  "wiki": true
}'

# Mirror repository
url=${gitea_url}/api/v1/repos/migrate?access_token=${token}

response=$(curl -X POST ${url} -H "accept: application/json" -H "Content-Type: application/json" -k -d "${repo}")
echo $response

# Additional settings
repo_settings='{
  "permissions": {
    "admin": true,
    "push": false,
    "pull": true
  }
}'

# Set additional repository parameters
url=${gitea_url}/api/v1/repos/${username}/${REPO_NAME}?access_token=${token}

response=$(curl -X PATCH ${url} -H "accept: application/json" -H "Content-Type: application/json" -k -d "${repo_settings}")
echo $response
