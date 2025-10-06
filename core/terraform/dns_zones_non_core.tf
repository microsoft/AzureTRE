# the zones defined in this file aren't used by the core system,
# but are a preperation for shared/workspace services deployment.

resource "azurerm_private_dns_zone" "non_core" {
  for_each            = local.private_dns_zone_names_non_core
  name                = each.key
  resource_group_name = azurerm_resource_group.core.name
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

# since shared services are in the core network, their dns link could exist once and must be defined here.
resource "azurerm_private_dns_zone_virtual_network_link" "mysql" {
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = module.network.core_vnet_id
  private_dns_zone_name = azurerm_private_dns_zone.non_core["privatelink.mysql.database.azure.com"].name
  name                  = azurerm_private_dns_zone.non_core["privatelink.mysql.database.azure.com"].name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_database" {
  name                  = "azure-database-link"
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = module.network.core_vnet_id
  private_dns_zone_name = azurerm_private_dns_zone.non_core["privatelink.database.windows.net"].name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azure_synapse" {
  name                  = "azure-synapse-link"
  resource_group_name   = azurerm_resource_group.core.name
  virtual_network_id    = module.network.core_vnet_id
  private_dns_zone_name = azurerm_private_dns_zone.non_core["privatelink.sql.azuresynapse.net"].name
  registration_enabled  = false
  tags                  = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "time_sleep" "azure_data_dns_zones" {
  depends_on = [
    azurerm_private_dns_zone_virtual_network_link.azure_database,
    azurerm_private_dns_zone_virtual_network_link.azure_synapse
  ]

  create_duration = "15s"
}

resource "null_resource" "add_a_dns_records" {
  count = anytrue([
    for r in local.env_rules :
    length(regexall(r.match, var.tre_id)) > 0
  ]) ? 1 : 0
  provisioner "local-exec" {
    command = "${path.root}/add_a_records.sh"
    #on_failure = continue
    environment = {
      TENANT_ID                            = data.azurerm_client_config.current.tenant_id
      ARM_CLIENT_ID                        = data.azurerm_key_vault_secret.arm_client_id.value
      ARM_CLIENT_SECRET                    = data.azurerm_key_vault_secret.arm_client_secret.value
      DATA_SHARED_RG                       = "rg-${var.tre_id}-data-shared"
      SQL_VM_NAME                          = "c${local.data_environment}wsafedb01"
      SQL_RECORD_SET_NAME                  = "c${local.data_environment}wsafedb01"
      CORE_RESOURCE_GROUP                  = local.core_resource_group_name
      SQL_ZONE_NAME                        = azurerm_private_dns_zone.non_core["privatelink.database.windows.net"].name
      PE_SYNAPSE_SQL                       = "pe-c${local.data_environment}synshared-sql"
      PE_SYNAPSE_SQL_ONDEMAND              = "pe-c${local.data_environment}synshared-sqlondemand"
      SYNAPSE_SQL_RECORD_SET_NAME          = "c${local.data_environment}synshared"
      SYNAPSE_SQL_ONDEMAND_RECORD_SET_NAME = "c${local.data_environment}synshared-ondemand"
      SYNAPSE_ZONE_NAME                    = azurerm_private_dns_zone.non_core["privatelink.sql.azuresynapse.net"].name
    }
  }

  depends_on = [
    time_sleep.azure_data_dns_zones
  ]
}
