mock_provider "azurerm" {
  override_during = plan
  mock_resource "azurerm_key_vault" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.KeyVault/vaults/kv-acme-test"
    }
  }
}

variables {
  vault_name                      = "kv-acme-test"
  location                        = "switzerlandnorth"
  resource_group_name             = "rg-test"
  tenant_id                       = "00000000-0000-0000-0000-000000000001"
  resource_processor_principal_id = "00000000-0000-0000-0000-000000000002"
  deployer_principal_id           = "00000000-0000-0000-0000-000000000003"
  shared_subnet_id                = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/SharedSubnet"
  private_dns_zone_id             = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.Network/privateDnsZones/privatelink.vaultcore.azure.net"
  log_analytics_workspace_id      = "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-test/providers/Microsoft.OperationalInsights/workspaces/logs-test"
  tags                            = { tre_id = "test" }
}

run "disabled_by_default" {
  command = plan

  assert {
    condition = (
      length(azurerm_key_vault.cache) == 0 &&
      length(azurerm_private_endpoint.cache) == 0 &&
      length(azurerm_role_assignment.resource_processor_certificates) == 0 &&
      length(azurerm_role_assignment.resource_processor_secrets) == 0 &&
      length(azurerm_role_assignment.deployer) == 0 &&
      length(azurerm_monitor_diagnostic_setting.cache) == 0 &&
      output.vault_name == ""
    )
    error_message = "Normal deployments must not create a cache vault, endpoint or access grants."
  }
}

run "isolated_ci_cache" {
  command = plan
  variables {
    enabled = true
  }

  assert {
    condition = (
      !azurerm_key_vault.cache[0].public_network_access_enabled &&
      azurerm_key_vault.cache[0].rbac_authorization_enabled &&
      azurerm_key_vault.cache[0].purge_protection_enabled &&
      azurerm_key_vault.cache[0].network_acls[0].default_action == "Deny" &&
      azurerm_key_vault.cache[0].network_acls[0].bypass == "None"
    )
    error_message = "The CI cache must use RBAC, private access and the default purge protection."
  }

  assert {
    condition = (
      azurerm_private_endpoint.cache[0].subnet_id == var.shared_subnet_id &&
      azurerm_private_endpoint.cache[0].private_dns_zone_group[0].private_dns_zone_ids == tolist([var.private_dns_zone_id]) &&
      azurerm_private_endpoint.cache[0].private_service_connection[0].private_connection_resource_id == azurerm_key_vault.cache[0].id &&
      azurerm_private_endpoint.cache[0].private_service_connection[0].subresource_names == tolist(["Vault"])
    )
    error_message = "The vault must connect through the TRE shared subnet and existing private DNS zone."
  }

  assert {
    condition = (
      azurerm_role_assignment.resource_processor_certificates[0].scope == azurerm_key_vault.cache[0].id &&
      azurerm_role_assignment.resource_processor_certificates[0].principal_id == var.resource_processor_principal_id &&
      azurerm_role_assignment.resource_processor_certificates[0].role_definition_name == "Key Vault Certificates Officer" &&
      azurerm_role_assignment.resource_processor_secrets[0].scope == azurerm_key_vault.cache[0].id &&
      azurerm_role_assignment.resource_processor_secrets[0].principal_id == var.resource_processor_principal_id &&
      azurerm_role_assignment.resource_processor_secrets[0].role_definition_name == "Key Vault Secrets User" &&
      azurerm_role_assignment.deployer[0].scope == azurerm_key_vault.cache[0].id &&
      azurerm_role_assignment.deployer[0].principal_id == var.deployer_principal_id &&
      azurerm_role_assignment.deployer[0].role_definition_name == "Key Vault Administrator"
    )
    error_message = "Cache access must be scoped to this vault and the resource processor and CI deployer identities."
  }

  assert {
    condition = (
      azurerm_monitor_diagnostic_setting.cache[0].target_resource_id == azurerm_key_vault.cache[0].id &&
      azurerm_monitor_diagnostic_setting.cache[0].log_analytics_workspace_id == var.log_analytics_workspace_id &&
      one(azurerm_monitor_diagnostic_setting.cache[0].enabled_log).category == "AuditEvent"
    )
    error_message = "Retained certificate access must be audited in the TRE log workspace."
  }
}
