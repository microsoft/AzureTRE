#!/bin/bash
set -e

function usage() {
    cat <<USAGE

    Usage: $0  [-t --tre-id] 

    Options:
        -t, --tre-id               ID of the TRE
        -g, --github-repo          URL to the github repo to clone e.g "https://github.com/Microsoft/AzureTRE"
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    -t | --tre-id)
        shift
        tre_id=$1
        ;;
    -g | --github-repo)
        shift
        github_repo=$1
        ;;

    esac
    shift # remove the current value for `$1` and use the next
done

# These variables need to be set
# ******************************
# tre-id=
# github-repo=


username=gitea-admin

keyVaultName="kv-"$tre_id
tokenSecretName="gitea-"$tre_id"-admin-token"
pwdSecretName="gitea-"$tre_id"-admin-password"

giteaUrl="https://gitea-$tre_id.azurewebsites.net"

# Check if access token exists
tokenExists=$(az keyvault secret list --vault-name $keyVaultName --query "contains([].id, 'https://$keyVaultName.vault.azure.net/secrets/$tokenSecretName')")


if $tokenExists
then
  response=$(az keyvault secret show --vault-name $keyVaultName --name $tokenSecretName)
  token=$(jq -r '.value' <<< "$response")
fi


if [ -z $token ] || [ "$token" = "null" ] 
then
  # Get admin password from keyvault
  response=$(az keyvault secret show --vault-name $keyVaultName --name $pwdSecretName)
  password=$(jq -r '.value' <<< "$response")
  
  credentials=$username:$password
  data='{"name": "'${username}'"}'
  url=${giteaUrl}/api/v1/users/${username}/tokens
  echo $credentials
  # Create new access token
  response=$(curl -X POST -H "Content-Type: application/json" -k -d "${data}" -u ${credentials} ${url})
  token=$(jq -r '.sha1' <<< "$response")
  echo $response
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
url=${giteaUrl}/api/v1/repos/migrate?access_token=${token}

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
url=${giteaUrl}/api/v1/repos/${username}/${REPO_NAME}?access_token=${token}

response=$(curl -X PATCH ${url} -H "accept: application/json" -H "Content-Type: application/json" -k -d "${repo_settings}")
echo $response
