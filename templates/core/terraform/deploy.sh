cat >core_backend.tf <<TRE_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_resource_group_name"
    storage_account_name = "$TF_VAR_mgmt_storage_account_name"
    container_name       = "$TF_VAR_terraform_state_container_name"
    key                  = "$TRE_ID"
  }
}
TRE_BACKEND

export TF_VAR_docker_registry_server="$ACR_NAME.azurecr.io"
export TF_VAR_docker_registry_username=$ACR_NAME
export TF_VAR_docker_registry_password=$(az acr credential show --name ${ACR_NAME} --query passwords[0].value -o tsv | sed 's/"//g')
export TF_VAR_management_api_image_tag=$IMAGE_TAG

terraform init -input=false -backend=true -reconfigure
terraform plan
terraform apply -auto-approve