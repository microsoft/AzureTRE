#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

register_resource_providers() {
  local providers=("Microsoft.Storage" "Microsoft.AlertsManagement" "Microsoft.Compute")
  echo -e "\e[34m»»» 🔧 \e[96mEnsuring required Azure resource providers are registered\e[0m"

  local provider status
  for provider in "${providers[@]}"; do
    status=$(az provider show --namespace "${provider}" --query registrationState --output tsv 2>/dev/null || echo "NotRegistered")
    if [[ "${status}" != "Registered" ]]; then
      echo -e "\e[34m»»»   Registering ${provider}"
      az provider register --namespace "${provider}" > /dev/null
      echo -e "\e[34m»»»   ${provider} registration submitted"
    else
      echo -e "\e[34m»»»   ${provider} already registered"
    fi
  done

  local feature_status
  feature_status=$(az feature show --namespace Microsoft.Compute --name EncryptionAtHost --query properties.state --output tsv 2>/dev/null || echo "NotRegistered")
  case "${feature_status}" in
    Registered)
      echo -e "\e[34m»»»   EncryptionAtHost feature already registered"
      ;;
    Pending)
      echo -e "\e[34m»»»   EncryptionAtHost feature registration is still pending"
      ;;
    NotRegistered|NotFound)
      echo -e "\e[34m»»»   Registering EncryptionAtHost feature"
      az feature register --namespace Microsoft.Compute --name EncryptionAtHost > /dev/null
      echo -e "\e[34m»»»   EncryptionAtHost feature registration submitted"
      ;;
    *)
      echo -e "\e[31m»»» ⚠️ Unexpected EncryptionAtHost feature status: ${feature_status}\e[0m"
      ;;
  esac
}

register_resource_providers
