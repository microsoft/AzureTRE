variable "tre_id" {
  type        = string
  description = "Unique TRE ID"
}

variable "location" {
  type        = string
  description = "Azure location (region) for deployment of core TRE services"
}

variable "storage_account_name" {
  type        = string
  description = "The name of the storage account to use"
}
