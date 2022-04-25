resource "azurerm_resource_group" "ws" {
  location = var.location
  name     = "rg-${local.workspace_resource_name_suffix}"
  tags = {
    project = "Azure Trusted Research Environment"
    tre_id  = var.tre_id
    source  = "https://github.com/microsoft/AzureTRE/"
  }

  lifecycle { ignore_changes = [tags] }
}

// Networking is causing dependencies issues when some parts are deployed from
// Azure, especially for storage shares. It became quite difficult to figure out the needed
// dependencies for each resource seperatly, so to make it easier we packed all network
// resources as a single module that should be depended on.
module "network" {
  source                 = "./network"
  location               = var.location
  tre_id                 = var.tre_id
  address_space          = var.address_space
  ws_resource_group_name = azurerm_resource_group.ws.name
  tre_resource_id        = var.tre_resource_id
}

module "aad" {
  source                         = "./aad"
  count                          = var.register_aad_application ? 1 : 0
  key_vault_id                   = azurerm_key_vault.kv.id
  workspace_resource_name_suffix = local.workspace_resource_name_suffix
  depends_on = [
    azurerm_key_vault_access_policy.deployer,
    azurerm_key_vault_access_policy.resource_processor,
    azurerm_private_endpoint.kvpe
  ]
}
