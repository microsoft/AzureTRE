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
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=fa7a3809a24f97d43737eaf72ed13eaef70fb369"
  arm_environment = var.arm_environment
}
