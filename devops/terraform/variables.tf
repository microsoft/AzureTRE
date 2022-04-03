variable "mgmt_storage_account_name" {
  type        = string
  description = "Storage account created by bootstrap to hold all Terraform state"
}

variable "mgmt_resource_group_name" {
  type        = string
  description = "Shared management resource group"
}

variable "location" {
  type        = string
  description = "Location used for all resources"

  validation {
    condition     = contains(["brazilsouth",
                              "canadacentral",
                              "centralusstage",
                              "eastus",
                              "eastus2",
                              "southcentralus",
                              "westus2",
                              "westus3",
                              "usgovvirginia",
                              "francecentral",
                              "germanywestcentral",
                              "northeurope",
                              "norwayeast",
                              "uksouth",
                              "westeurope",
                              "swedencentral",
                              "switzerlandnorth",
                              "southafricanorth",
                              "australiaeast",
                              "centralindia",
                              "japaneast",
                              "koreacentral",
                              "southeastasia",
                              "eastasia",
                              "chinanorth3"],
                              var.location)
    error_message = "Location should be within an availability zones please select one of the following: https://docs.microsoft.com/en-us/azure/availability-zones/az-overview."
  }
}

variable "acr_sku" {
  type        = string
  default     = "Standard"
  description = "Price tier for ACR"
}

variable "acr_name" {
  type        = string
  description = "Name of ACR"
}
