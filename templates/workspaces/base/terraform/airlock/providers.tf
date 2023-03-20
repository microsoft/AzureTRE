terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.8.0"
    }
  }
}

module "cloud_settings" {
  source          = "../cloud_settings"
  arm_environment = var.arm_environment
}
