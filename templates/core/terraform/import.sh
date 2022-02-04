export TF_VAR_docker_registry_server="$TF_VAR_acr_name.azurecr.io"
export TF_VAR_docker_registry_username=$TF_VAR_acr_name
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_acr_name} --query passwords[0].value -o tsv | sed 's/"//g')

export TF_LOG=""

cd ./templates/core/terraform/

terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=$TF_VAR_mgmt_resource_group_name" \
    -backend-config="storage_account_name=$TF_VAR_mgmt_storage_account_name" \
    -backend-config="container_name=$TF_VAR_terraform_state_container_name" \
    -backend-config="key=${TRE_ID}"

terraform import module.jumpbox.azurerm_key_vault_secret.jumpbox_credentials "https://kv-${TRE_ID}.vault.azure.net/secrets/vm-${TRE_ID}-jumpbox-admin-credentials/e6ae209811894395bd50a846e18d1782"

terraform import module.appgateway.azurerm_key_vault_certificate.tlscert "https://kv-${TRE_ID}.vault.azure.net/certificates/letsencrypt/6e5a17562a464283804cc9795479cfb7"

terraform import module.resource_processor_vmss_porter[0].azurerm_key_vault_secret.resource_processor_vmss_password "https://kv-${TRE_ID}.vault.azure.net/secrets/resource-processor-vmss-password/27d8225bd9ba49369cf40d607732bd9c"

terraform import module.gitea[0].azurerm_key_vault_secret.gitea_password "https://kv-${TRE_ID}.vault.azure.net/secrets/gitea-${TRE_ID}-admin-password/666122b4526447fda428b2bc3f1fff23"

terraform import module.gitea[0].azurerm_key_vault_secret.db_password "https://kv-${TRE_ID}.vault.azure.net/secrets/mysql-${TRE_ID}-password/cf5414d7b3fa4da79f5ce8e6a62c7a8e"
