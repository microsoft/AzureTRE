# Local tflint configuration for azureml workspace service
# Disables remote module loading to avoid linting errors with external modules

config {
  call_module_type = "local"
  force = false
}

plugin "azurerm" {
    enabled = true
}

rule "azurerm_resource_missing_tags" {
  enabled = true
  tags = ["tre_id", "tre_workspace_id", "tre_workspace_service_id"]
}
