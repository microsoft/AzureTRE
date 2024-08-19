# openai cognitive services account

resource "azurerm_cognitive_account" "openai" {
  kind                = "OpenAI"
  name                = "openai-${var.tre_id}-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
  location            = data.azurerm_resource_group.ws.location
  sku_name            = "S0"
}

locals {
  openai_model_name = "gpt-35-turbo"
  openai_model_version = "0301"
}

resource "azurerm_cognitive_deployment" "openai" {
  name                 = "openai-${local.openai_model_name}-${local.openai_model_version}-${var.tre_id}-${local.short_workspace_id}"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
#    name    = "gpt-4-32k"
    name    = local.openai_model_name
#    version = "0314"
    version = local.openai_model_version
  }

  scale {
    type = "Standard"
  }
}

resource "azurerm_private_dns_zone" "openai" {
  name                = "privatelink.openai.azure.com"
  resource_group_name = data.azurerm_resource_group.ws.name
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
    private_dns_zone_ids = [azurerm_private_dns_zone.openai.id]
  }

  lifecycle { ignore_changes = [tags] }
}
