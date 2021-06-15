cat > service_backend.tf <<TRE_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_resource_group_name"
    storage_account_name = "$TF_VAR_mgmt_storage_account_name"
    container_name       = "$TF_VAR_terraform_state_container_name"
    key                  = "${TRE_ID}${WORKSPACE_ID}azureml"
  }
}
TRE_BACKEND

terraform init -input=false -backend=true -reconfigure
terraform plan
terraform apply -auto-approve