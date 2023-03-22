terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.8.0"
    }
  }
}


module "terraform_azurerm_environment_configuration" {
  source = "github.com/microsoft/AzureTRE-modules/terraform_azurerm_environment_configuration"
  arm_environment = var.arm_environment
}
