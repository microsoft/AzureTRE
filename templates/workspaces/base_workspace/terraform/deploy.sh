cat > workspace_backend.tf <<TRE_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_res_group"
    storage_account_name = "$TF_VAR_state_storage"
    container_name       = "$TF_VAR_state_container"
    key                  = "$TF_VAR_resource_name_prefix$TF_VAR_environment$TF_VAR_ws_id"
  }
}
TRE_BACKEND

terraform init -input=false -backend=true -reconfigure
terraform plan
terraform apply -auto-approve