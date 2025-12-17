data "azurerm_client_config" "current" {
  provider = azurerm.core
}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_resource_group" "core" {
  provider = azurerm.core
  name     = "rg-${var.tre_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_linux_web_app" "guacamole" {
  name                = "guacamole-${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_parent_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_public_ip" "app_gateway_ip" {
  provider            = azurerm.core
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}

data "azurerm_key_vault_key" "ws_encryption_key" {
  count        = var.enable_cmk_encryption ? 1 : 0
  name         = local.cmk_name
  key_vault_id = var.key_store_id
}

data "azurerm_user_assigned_identity" "ws_encryption_identity" {
  count               = var.enable_cmk_encryption ? 1 : 0
  name                = local.encryption_identity_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "template_file" "get_apt_keys" {
  template = file("${path.module}/get_apt_keys.sh")
  vars = {
    NEXUS_PROXY_URL = local.nexus_proxy_url
  }
}

data "template_file" "pypi_sources_config" {
  template = file("${path.module}/pypi_sources_config.sh")
  vars = {
    nexus_proxy_url = local.nexus_proxy_url
  }
}

data "template_file" "apt_sources_config" {
  template = file("${path.module}/apt_sources_config.yml")
  vars = {
    nexus_proxy_url = local.nexus_proxy_url
    apt_sku         = local.apt_sku
  }
}

data "azurerm_storage_account" "stg" {
  name                = local.storage_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

# External data source to fetch username with graceful fallback for deleted users
data "external" "username" {
  count = var.admin_username == "" ? 1 : 0
  program = ["bash", "${path.module}/get_username.sh"]
  
  query = {
    owner_id      = var.owner_id
    tenant_id     = var.auth_tenant_id
    client_id     = var.auth_client_id
    client_secret = var.auth_client_secret
  }
}

locals {
  # Compute username with graceful fallback
  # Priority: explicit admin_username > friendly username from external script > should never fail
  computed_admin_username = var.admin_username != "" ? var.admin_username : data.external.username[0].result.username
}
