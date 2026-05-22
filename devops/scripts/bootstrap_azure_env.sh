#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to debug (will echo secrets!)
# set -o xtrace

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
REPO_ROOT="${SCRIPT_DIR}/../.."

print_header() {
  echo -e "\n\e[34m╔══════════════════════════════════════╗"
  echo -e "║          \e[33mAzure TRE Makefile\e[34m          ║"
  echo -e "╚══════════════════════════════════════╝"
  echo -e "\n\e[34m»»» ✅ \e[96mInitializing Azure environment\e[0m..."
}

load_environment_config() {
  if [[ -z "${USE_ENV_VARS_NOT_FILES:-}" ]]; then
    if [[ ! -f "${REPO_ROOT}/config.yaml" ]]; then
      echo -e "\e[31m»»» ⚠️ Your config.yaml file has not been set up! 😥 Please create a config.yaml file.\e[0m"
      exit 1
    fi
    # shellcheck disable=SC1091
    DIR="${SCRIPT_DIR}" . "${SCRIPT_DIR}/load_and_validate_env.sh"
  fi
}

ensure_automation_login() {
  if [[ -n "${TF_IN_AUTOMATION:-}" ]]; then
    if [[ -n "${ARM_CLIENT_SECRET:-}" ]]; then
      echo "Warning: Using classic service principal authentication."
      az cloud set --name "${AZURE_ENVIRONMENT}"
      az login --service-principal -u "${ARM_CLIENT_ID}" -p "${ARM_CLIENT_SECRET}" --tenant "${ARM_TENANT_ID}"
      az account set -s "${ARM_SUBSCRIPTION_ID}"
    fi
  fi
}

set_account_context() {
  local subscription_name
  subscription_name=$(az account show --query name -o tsv 2>/dev/null || true)
  if [[ -z "${subscription_name}" ]]; then
    echo -e "\n\e[31m»»» ⚠️ You are not logged in to Azure!\e[0m"
    exit 1
  fi

  SUB_ID_VALUE="$(az account show --query id -o tsv)"
  TENANT_ID_VALUE="$(az account show --query tenantId -o tsv)"

  export SUB_ID="${SUB_ID_VALUE}"
  export TENANT_ID="${TENANT_ID_VALUE}"

  export ARM_STORAGE_USE_AZUREAD=true
  export ARM_USE_AZUREAD=true

  echo -e "\e[34m»»» 🔨 \e[96mAzure details from logged on user \e[0m"
  echo -e "\e[34m»»»   • \e[96mSubscription: \e[33m${subscription_name}\e[0m"
  echo -e "\e[34m»»»   • \e[96mTenant:       \e[33m${TENANT_ID}\e[0m\n"
}

print_header
load_environment_config
ensure_automation_login
set_account_context

# Ensure nounset is restored to avoid affecting caller
set +o nounset
