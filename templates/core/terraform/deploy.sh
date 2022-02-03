export TF_VAR_docker_registry_server="$TF_VAR_acr_name.azurecr.io"
export TF_VAR_docker_registry_username=$TF_VAR_acr_name
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_acr_name} --query passwords[0].value -o tsv | sed 's/"//g')

PLAN_FILE="tfplan$$"
LOG_FILE="tmp$$.log"

../../../devops/scripts/terraform_wrapper.sh \
  -g $TF_VAR_mgmt_resource_group_name \
  -s $TF_VAR_mgmt_storage_account_name \
  -n $TF_VAR_terraform_state_container_name \
  -k ${TRE_ID} \
  -l ${LOG_FILE} \
  -c "terraform import module.appgateway.azurerm_key_vault_certificate.tlscert https://kv-tregithub.vault.azure.net/secrets/letsencrypt/6e5a17562a464283804cc9795479cfb7 && \
  terraform import module.gitea[0].azurerm_key_vault_secret.gitea_password https://kv-tregithub.vault.azure.net/secrets/gitea-tregithub-admin-password/666122b4526447fda428b2bc3f1fff23 && \
  terraform plan -out ${PLAN_FILE} && \
  terraform apply -input=false -auto-approve ${PLAN_FILE} && \
  terraform output -json > ../tre_output.json"

