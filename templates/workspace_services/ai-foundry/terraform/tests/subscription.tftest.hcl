# Mocks verify subscription selection and resource scopes without contacting Azure.
# Python regression checks also inspect provider configuration expressions.

mock_provider "azurerm" {
  alias = "core"
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000001"
      tenant_id       = "00000000-0000-0000-0000-000000000002"
    }
  }
  mock_data "azurerm_private_dns_zone" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com"
    }
  }
}

mock_provider "azurerm" {
  mock_data "azurerm_resource_group" {
    defaults = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test"
      name     = "rg-test"
      location = "switzerlandnorth"
    }
  }
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000001"
      tenant_id       = "00000000-0000-0000-0000-000000000002"
    }
  }
  mock_data "azurerm_subnet" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/ServicesSubnet"
    }
  }
  mock_data "azurerm_private_dns_zone" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com"
    }
  }
  mock_data "azurerm_key_vault" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.KeyVault/vaults/kv-test"
    }
  }
  mock_resource "azurerm_cognitive_account" {
    defaults = {
      id                 = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.CognitiveServices/accounts/aif-test"
      primary_access_key = null
    }
  }
  mock_data "azurerm_cognitive_account" {
    defaults = {
      primary_access_key = "synthetic-key-from-account-lookup"
    }
  }
  mock_resource "azurerm_key_vault_secret" {
    defaults = {
      versionless_id          = "https://kv-test.vault.azure.net/secrets/aif-test-access-key"
      resource_versionless_id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.KeyVault/vaults/kv-test/secrets/aif-test-access-key"
    }
  }
}

mock_provider "azurerm" {
  alias = "distinct"
  mock_data "azurerm_resource_group" {
    defaults = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000005/resourceGroups/rg-test"
      name     = "rg-test"
      location = "switzerlandnorth"
    }
  }
  mock_data "azurerm_client_config" {
    defaults = {
      subscription_id = "00000000-0000-0000-0000-000000000005"
      tenant_id       = "00000000-0000-0000-0000-000000000002"
    }
  }
  mock_data "azurerm_subnet" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000005/resourceGroups/rg-test/providers/Microsoft.Network/virtualNetworks/vnet-test/subnets/ServicesSubnet"
    }
  }
  mock_data "azurerm_private_dns_zone" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000005/resourceGroups/rg-test/providers/Microsoft.Network/privateDnsZones/privatelink.openai.azure.com"
    }
  }
  mock_data "azurerm_key_vault" {
    defaults = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000005/resourceGroups/rg-test/providers/Microsoft.KeyVault/vaults/kv-test"
    }
  }
  mock_resource "azurerm_cognitive_account" {
    defaults = {
      id                 = "/subscriptions/00000000-0000-0000-0000-000000000005/resourceGroups/rg-test/providers/Microsoft.CognitiveServices/accounts/aif-test"
      primary_access_key = null
    }
  }
  mock_data "azurerm_cognitive_account" {
    defaults = {
      primary_access_key = "synthetic-key-from-account-lookup"
    }
  }
  mock_resource "azurerm_key_vault_secret" {
    defaults = {
      versionless_id          = "https://kv-test.vault.azure.net/secrets/aif-test-access-key"
      resource_versionless_id = "/subscriptions/00000000-0000-0000-0000-000000000005/resourceGroups/rg-test/providers/Microsoft.KeyVault/vaults/kv-test/secrets/aif-test-access-key"
    }
  }
}

mock_provider "azapi" {
  mock_data "azapi_resource_action" {
    defaults = {
      output = {
        value = [{
          format          = "OpenAI"
          name            = "gpt-5.1"
          version         = "2025-11-13"
          lifecycleStatus = "GenerallyAvailable"
          capabilities    = { chatCompletion = "true" }
          skus            = [{ name = "Standard", usageName = "OpenAI.Standard.gpt-5.1" }]
        }]
      }
    }
  }
}

mock_provider "time" {}

variables {
  workspace_id                   = "00000000-0000-0000-0000-000000001234"
  tre_resource_id                = "00000000-0000-0000-0000-000000005678"
  tre_id                         = "test"
  workspace_owners_group_id      = "00000000-0000-0000-0000-000000000003"
  workspace_researchers_group_id = "00000000-0000-0000-0000-000000000004"
  local_auth_enabled             = true
}

run "default_subscription" {
  command   = apply
  state_key = "default_subscription"
  providers = {
    azurerm      = azurerm
    azurerm.core = azurerm.core
    azapi        = azapi
    time         = time
  }

  assert {
    condition = (
      local.workspace_subscription_id == "00000000-0000-0000-0000-000000000001"
      && data.azurerm_client_config.current.subscription_id == "00000000-0000-0000-0000-000000000001"
      && azapi_resource_action.purge_ai_foundry.resource_id == "/subscriptions/00000000-0000-0000-0000-000000000001/providers/Microsoft.CognitiveServices/locations/switzerlandnorth/resourceGroups/rg-test-ws-1234/deletedAccounts/aif-test-ws-1234-svc-5678"
    )
    error_message = "Subscription selection and purge must target the workspace, with core as the default."
  }

  assert {
    condition = alltrue([for id in [
      data.azurerm_resource_group.ws.id,
      data.azurerm_subnet.services.id,
      data.azurerm_key_vault.ws[0].id,
      azurerm_cognitive_account.ai_foundry.id,
      azurerm_key_vault_secret.openai_api_key[0].resource_versionless_id
    ] : startswith(id, "/subscriptions/00000000-0000-0000-0000-000000000001/")])
    error_message = "Workspace lookups, the account and the secret must use the workspace provider."
  }

  assert {
    condition = (
      alltrue([for id in azurerm_private_endpoint.ai_foundry.private_dns_zone_group[0].private_dns_zone_ids :
        startswith(id, "/subscriptions/00000000-0000-0000-0000-000000000001/")
      ])
      && alltrue([for zone in [
        data.azurerm_private_dns_zone.cognitive_services,
        data.azurerm_private_dns_zone.openai,
        data.azurerm_private_dns_zone.ai_services
      ] : startswith(zone.id, "/subscriptions/00000000-0000-0000-0000-000000000001/")])
    )
    error_message = "Every private DNS zone must come from the core provider."
  }

  assert {
    condition = (
      azurerm_key_vault_secret.openai_api_key[0].key_vault_id == data.azurerm_key_vault.ws[0].id
      && alltrue([for assignment in azurerm_role_assignment.inference :
        assignment.scope == azurerm_cognitive_account.ai_foundry.id
      ])
      && alltrue([for assignment in azurerm_role_assignment.api_key_reader :
        assignment.scope == azurerm_key_vault_secret.openai_api_key[0].resource_versionless_id
      ])
    )
    error_message = "The secret and role scopes must stay within the workspace subscription."
  }
}

run "distinct_subscription" {
  command   = apply
  state_key = "distinct_subscription"
  providers = {
    azurerm      = azurerm.distinct
    azurerm.core = azurerm.core
    azapi        = azapi
    time         = time
  }

  variables {
    workspace_subscription_id = "00000000-0000-0000-0000-000000000005"
  }

  assert {
    condition = (
      local.workspace_subscription_id == "00000000-0000-0000-0000-000000000005"
      && data.azurerm_client_config.current.subscription_id == "00000000-0000-0000-0000-000000000001"
      && azapi_resource_action.purge_ai_foundry.resource_id == "/subscriptions/00000000-0000-0000-0000-000000000005/providers/Microsoft.CognitiveServices/locations/switzerlandnorth/resourceGroups/rg-test-ws-1234/deletedAccounts/aif-test-ws-1234-svc-5678"
    )
    error_message = "Subscription selection and purge must target the workspace, with core as the default."
  }

  assert {
    condition = alltrue([for id in [
      data.azurerm_resource_group.ws.id,
      data.azurerm_subnet.services.id,
      data.azurerm_key_vault.ws[0].id,
      azurerm_cognitive_account.ai_foundry.id,
      azurerm_key_vault_secret.openai_api_key[0].resource_versionless_id
    ] : startswith(id, "/subscriptions/00000000-0000-0000-0000-000000000005/")])
    error_message = "Workspace lookups, the account and the secret must use the workspace provider."
  }

  assert {
    condition = (
      alltrue([for id in azurerm_private_endpoint.ai_foundry.private_dns_zone_group[0].private_dns_zone_ids :
        startswith(id, "/subscriptions/00000000-0000-0000-0000-000000000001/")
      ])
      && alltrue([for zone in [
        data.azurerm_private_dns_zone.cognitive_services,
        data.azurerm_private_dns_zone.openai,
        data.azurerm_private_dns_zone.ai_services
      ] : startswith(zone.id, "/subscriptions/00000000-0000-0000-0000-000000000001/")])
    )
    error_message = "Every private DNS zone must come from the core provider."
  }

  assert {
    condition = (
      azurerm_key_vault_secret.openai_api_key[0].key_vault_id == data.azurerm_key_vault.ws[0].id
      && alltrue([for assignment in azurerm_role_assignment.inference :
        assignment.scope == azurerm_cognitive_account.ai_foundry.id
      ])
      && alltrue([for assignment in azurerm_role_assignment.api_key_reader :
        assignment.scope == azurerm_key_vault_secret.openai_api_key[0].resource_versionless_id
      ])
    )
    error_message = "The secret and role scopes must stay within the workspace subscription."
  }
}
