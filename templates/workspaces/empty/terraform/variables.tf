variable "resource_group_prefix" {
  type        = string
  description = "Resource group  prefix"
}

data "azurerm_resource_group" "core" {
  name = "${var.resource_group_prefix}-${var.tre_id}"
}

variable "core_vnet_name" {
  type        = string
  description = "shared_services vnet name"
  default     = "vnet-core"
}
variable "dns_name" {
  type        = string
  description = "Workspace DNS name"
}

data "azurerm_virtual_network" "core" {
  name                = var.core_vnet_name
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_subnet" "shared_services_appgw" {
  name                 = "appGwSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_resource_group.core.name
}

data "azurerm_subnet" "shared_services_bastion" {
  name                 = "AzureBastionSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_resource_group.core.name
}

data "azurerm_subnet" "shared_services" {
  name                 = "sharedServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_resource_group.core.name
}

variable "address_space" {
  type        = string
  description = "Workspace VNet address space"
}

variable "name" {
  type = string

  description = "Name of the workspace"
}

variable "tre_id" {
  type = string

  description = "Unique DRE instance id"
}

variable "workspace_id" {
  type        = string
  description = "Unique workspace id"
}

variable "tre_dns_suffix" {
  type        = string
  description = "DNS suffix for the environment. E.g. .dre.myorg.com or x.drelocal, must be >=2 segments in the suffix"
}

variable "location" {
  type = string

  description = "Azure region to deploy to"
}