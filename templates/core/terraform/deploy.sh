cat >core_backend.tf <<TRE_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_res_group"
    storage_account_name = "$TF_VAR_state_storage"
    container_name       = "$TF_VAR_state_container"
    key                  = "$TF_VAR_resource_name_prefix$TF_VAR_environment"
  }
}
TRE_BACKEND

ACR_NAME="${TF_VAR_resource_name_prefix}acr"
export TF_VAR_docker_registry_server="${TF_VAR_resource_name_prefix}acr.azurecr.io"
export TF_VAR_docker_registry_username="${TF_VAR_resource_name_prefix}acr"
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_resource_name_prefix}acr --query passwords[0].value -o tsv | sed 's/"//g')
export TF_VAR_management_api_image_tag=$TF_VAR_image_tag

terraform init -input=false -backend=true -reconfigure
terraform plan
terraform apply -auto-approve