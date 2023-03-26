terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.16"
    }
    local = {
      source  = "hashicorp/local"
      version = ">= 2.2"
    }
  }
}

module "terraform_azurerm_environment_configuration" {
  source          = "github.com/microsoft/terraform-azurerm-environment-configuration"
  arm_environment = var.arm_environment
}
