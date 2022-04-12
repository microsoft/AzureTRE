
variable "tre_id" {}

// We have to inject this via variable instead of getting via conventional
// data.azurerm_client_config.current.object_id due to a bug with TF & MSI
// https://github.com/hashicorp/terraform-provider-azurerm/issues/7787
variable "deployer_object_id" {
  type = string
}
