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

module "cloud_settings" {
  source          = "../../../cloud_settings"
  arm_environment = var.arm_environment
}
