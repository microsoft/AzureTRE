# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.46.0"
    }
  }
}

resource "azurerm_resource_group" "core" {
  location = var.location
  name     =  "${var.resource_group_prefix}-${var.tre_id}"
}

resource "azurerm_log_analytics_workspace" "tre" {
  name                = "loganalytics-tre-${var.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.location
  retention_in_days   = 30
  sku                 = "pergb2018"

}