# openai cognitive services account

resource "azurerm_cognitive_account" "openai" {
  kind                          = "OpenAI"
  name                          = "openai-${local.service_resource_name_suffix}"
  resource_group_name           = data.azurerm_resource_group.ws.name
  location                      = data.azurerm_resource_group.ws.location
  sku_name                      = "S0"
  custom_subdomain_name         = "openai-${local.service_resource_name_suffix}"
  public_network_access_enabled = var.is_exposed_externally
  tags                          = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_cognitive_deployment" "openai" {
  name                 = "openai-${local.openai_model.name}-${local.openai_model.version}-${local.service_resource_name_suffix}"
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = local.openai_model.name
    version = local.openai_model.version
  }

  scale {
    type = "Standard"
  }
}

resource "azurerm_private_endpoint" "openai_private_endpoint" {
  name                = "pe-${azurerm_cognitive_account.openai.name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    name                           = "psc-${azurerm_cognitive_account.openai.name}"
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = module.terraform_azurerm_environment_configuration.private_links["privatelink.openai.azure.com"]
    private_dns_zone_ids = [data.azurerm_private_dns_zone.openai.id]
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "${azurerm_cognitive_account.openai.name}-access-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}
