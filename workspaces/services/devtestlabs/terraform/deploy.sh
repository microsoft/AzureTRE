cat > service_backend.tf <<TRE_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_res_group"
    storage_account_name = "$TF_VAR_state_storage"
    container_name       = "$TF_VAR_state_container"
    key                  = "${TF_VAR_tre_id}-ws-${TF_VAR_workspace_id}-svc-virtual-desktop-dev-test-lab"
  }
}
TRE_BACKEND

terraform init -input=false -backend=true -reconfigure
terraform plan
terraform apply -auto-approve