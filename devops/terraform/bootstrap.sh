#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# shellcheck disable=SC1091
source ../scripts/terraform_init.sh

if [[ "${CI_BOOTSTRAP_LEASE_RECOVERY:-false}" == true ]]; then
  python3 ../scripts/recover_bootstrap_lease.py context
fi

check_role_assignments() {
  local roles
  # shellcheck disable=SC2154
  roles=$(az role assignment list \
    --assignee "$USER_OBJECT_ID" \
    --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name" \
    --query "[?roleDefinitionName=='Storage Blob Data Contributor'].roleDefinitionName" --output tsv)

  if [[ $roles == *"Storage Blob Data Contributor"* ]]; then
    return 0
  fi
  return 1
}

# Baseline Azure resources
echo -e "\n\e[34m»»» 🤖 \e[96mCreating resource group and storage account\e[0m..."
# The repository tag names the CI owner. Cleanup refuses groups that another repository tagged.
ci_tags=()
if [[ -n "${TF_VAR_ci_git_ref:-}" ]]; then
  ci_tags=("ci_git_ref=$TF_VAR_ci_git_ref")
  if [[ -n "${TF_VAR_ci_repository:-}" ]]; then
    ci_tags+=("ci_repository=$TF_VAR_ci_repository")
  fi
fi

# shellcheck disable=SC2154
group_exists=$(az group exists --name "$TF_VAR_mgmt_resource_group_name" --output json)
case "$group_exists" in
  true)
    # Verify existing ownership before bootstrap can update the CI tag.
    if [[ "${CI_BOOTSTRAP_LEASE_RECOVERY:-false}" == true ]]; then
      python3 ../scripts/recover_bootstrap_lease.py verify-owner
    fi
    # Never take over a group that another repository's CI tagged, also outside lease recovery.
    if [[ -n "${TF_VAR_ci_repository:-}" ]] && (( ${#ci_tags[@]} )); then
      # Azure tag names are not case-sensitive, so read the owner tag with any case. Read the whole
      # group, because az prints nothing for a query result of null, for example a group without tags.
      current_owner=$(az group show --name "$TF_VAR_mgmt_resource_group_name" --output json \
        | python3 -c 'import json, sys; sys.path.insert(0, "../scripts"); from ci_environment_id import ci_tags; print(ci_tags(json.load(sys.stdin).get("tags")).get("ci_repository") or "")')
      if [[ -n "${current_owner}" && "${current_owner,,}" != "${TF_VAR_ci_repository,,}" ]]; then
        echo "ERROR: The management resource group belongs to the CI of ${current_owner}." >&2
        exit 1
      fi
      # Keep this rule identical to repository_owns() in ci_environment_id.py. Main groups use
      # configured names, so the rule applies to PR and branch environments only.
      if [[ -z "${current_owner}" && "${TF_VAR_ci_git_ref}" != refs/heads/main && "${CI_ENV_PREFIX:-tre}" == tre \
        && "${TF_VAR_ci_repository,,}" != "microsoft/azuretre" ]]; then
        echo "ERROR: The untagged management resource group can belong to the upstream CI." >&2
        echo "If this repository created it, tag the core and management groups with ci_repository=${TF_VAR_ci_repository}." >&2
        exit 1
      fi
    fi
    # Creating an existing group without tags clears its tags. Preserve them on reruns.
    if (( ${#ci_tags[@]} )); then
      az group update --name "$TF_VAR_mgmt_resource_group_name" \
        --set "${ci_tags[@]/#/tags.}" -o table
    fi
    ;;
  false)
    # Tag new CI groups before any later bootstrap step can fail.
    if (( ${#ci_tags[@]} )); then
      az group create --resource-group "$TF_VAR_mgmt_resource_group_name" --location "$LOCATION" \
        --tags "${ci_tags[@]}" -o table
    else
      az group create --resource-group "$TF_VAR_mgmt_resource_group_name" --location "$LOCATION" -o table
    fi
    ;;
  *)
    echo "ERROR: Could not determine whether the management resource group exists." >&2
    exit 1
    ;;
esac

# shellcheck disable=SC2154
if ! az storage account show --resource-group "$TF_VAR_mgmt_resource_group_name" --name "$TF_VAR_mgmt_storage_account_name" --query "name" -o none 2>/dev/null; then
  # only run `az storage account create` if doesn't exist (to prevent error from occuring if storage account was originally created without infrastructure encryption enabled)

  # Set default encryption types based on enable_cmk
  encryption_type=$([ "${TF_VAR_enable_cmk_encryption:-false}" = true ] && echo "Account" || echo "Service")

  # shellcheck disable=SC2154
  az storage account create --resource-group "$TF_VAR_mgmt_resource_group_name" \
    --name "$TF_VAR_mgmt_storage_account_name" --location "$LOCATION" \
    --allow-blob-public-access false --min-tls-version TLS1_2 \
    --kind StorageV2 --sku Standard_LRS -o table \
    --encryption-key-type-for-queue "$encryption_type" \
    --encryption-key-type-for-table "$encryption_type" \
    --require-infrastructure-encryption true
else
  echo "Storage account already exists..."
  az storage account show --resource-group "$TF_VAR_mgmt_resource_group_name" --name "$TF_VAR_mgmt_storage_account_name" --output table
fi

# shellcheck disable=SC1091
source ../scripts/storage_enable_public_access.sh \
  --storage-account-name "${TF_VAR_mgmt_storage_account_name}" \
  --resource-group-name "${TF_VAR_mgmt_resource_group_name}"

# Grant user blob data contributor permissions
echo -e "\n\e[34m»»» 🔑 \e[96mGranting Storage Blob Data Contributor role to the current user\e[0m..."
if [ -n "${ARM_CLIENT_ID:-}" ]; then
    USER_OBJECT_ID=$(az ad sp show --id "$ARM_CLIENT_ID" --query id --output tsv)
else
    USER_OBJECT_ID=$(az ad signed-in-user show --query id --output tsv)
fi

# shellcheck disable=SC2154
az role assignment create --assignee "$USER_OBJECT_ID" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"

if ! retry_with_backoff check_role_assignments; then
  echo "ERROR: Timeout waiting for az role assignments."
  exit 1
fi


echo -e "\n\e[34m»»» 📦 \e[96mCreating storage containers\e[0m..."
# shellcheck disable=SC2154
containers=("$TF_VAR_terraform_state_container_name" "tflogs")
max_retries=8

for container in "${containers[@]}"; do
  for ((i=1; i<=max_retries; i++)); do
    if az storage container create --account-name "$TF_VAR_mgmt_storage_account_name" --name "$container" --auth-mode login -o table; then
      echo "Container '$container' created successfully."
      break
    else
      sleep 10
    fi
    if [ $i -eq $max_retries ]; then
      echo "ERROR: Failed to create container '$container' after $max_retries attempts."
      exit 1
    fi
  done
done

echo "Checking blob read, write and lease access before initialising Terraform..."
if ! retry_with_backoff check_blob_access; then
  echo "ERROR: Bootstrap blob access check failed. Terraform has not been started." >&2
  exit 1
fi

if [[ "${CI_BOOTSTRAP_LEASE_RECOVERY:-false}" == true ]]; then
  if ! python3 ../scripts/recover_bootstrap_lease.py recover; then
    echo "ERROR: Bootstrap lease recovery failed. Terraform has not been started." >&2
    exit 1
  fi
fi

echo -e "\n\e[34m»»» ✨ \e[96mTerraform init\e[0m..."
# shellcheck disable=SC2154
cat > bootstrap_backend.tf <<BOOTSTRAP_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_resource_group_name"
    storage_account_name = "$TF_VAR_mgmt_storage_account_name"
    container_name       = "$TF_VAR_terraform_state_container_name"
    key                  = "bootstrap.tfstate"
  }
}
BOOTSTRAP_BACKEND

# shellcheck disable=SC2154
if ! retry_with_backoff init_terraform bootstrap.tfstate; then
  echo "ERROR: Terraform backend initialisation failed. See the error above." >&2
  exit 1
fi
echo -e "\n\e[34m»»» 📤 \e[96mImporting resources to state\e[0m..."
if ! terraform state show azurerm_resource_group.mgmt > /dev/null; then
  echo  "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name"
  terraform import azurerm_resource_group.mgmt "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name"
fi

if ! terraform state show azurerm_storage_account.state_storage > /dev/null; then
  terraform import azurerm_storage_account.state_storage "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"
fi
echo "State imported"
set +o nounset
