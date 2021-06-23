cat > service_backend.tf <<TRE_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_resource_group_name"
    storage_account_name = "$TF_VAR_mgmt_storage_account_name"
    container_name       = "$TF_VAR_terraform_state_container_name"
    key                  = "${TF_VAR_tre_id}-ws-${TF_VAR_workspace_id}-svc-virtual-desktop-dev-test-lab"
  }
}
TRE_BACKEND

terraform init -input=false -backend=true -reconfigure -upgrade
terraform plan
terraform apply -auto-approve