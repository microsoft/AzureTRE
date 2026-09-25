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
}

run "private_model_only" {
  command = plan

  override_resource {
    target          = azurerm_cognitive_account.ai_foundry
    override_during = plan
    values = {
      id = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.CognitiveServices/accounts/aif-test"
    }
  }

  assert {
    condition = (
      azurerm_cognitive_account.ai_foundry.public_network_access_enabled == false
      && azurerm_cognitive_account.ai_foundry.local_auth_enabled == false
      && azurerm_cognitive_account.ai_foundry.outbound_network_access_restricted == true
      && toset(azurerm_cognitive_account.ai_foundry.fqdns) == toset(["deny-all.invalid"])
      && one(azurerm_cognitive_account.ai_foundry.network_acls).default_action == "Deny"
      && one(azurerm_cognitive_account.ai_foundry.network_acls).bypass == "None"
    )
    error_message = "The account must default to private networking and Entra authentication without trusted-service bypass."
  }

  assert {
    condition     = azurerm_cognitive_deployment.openai.version_upgrade_option == "NoAutoUpgrade"
    error_message = "Azure must not automatically upgrade the selected model version."
  }

  assert {
    condition = (
      azurerm_cognitive_account_project.default.tags["tre_id"] == var.tre_id
      && azurerm_cognitive_account_project.default.tags["tre_workspace_id"] == var.workspace_id
      && azurerm_cognitive_account_project.default.tags["tre_workspace_service_id"] == var.tre_resource_id
    )
    error_message = "The project must carry the TRE, workspace and workspace service identifiers as tags."
  }

  assert {
    condition = (
      length(data.azurerm_key_vault.ws) == 0
      && length(azurerm_key_vault_secret.openai_api_key) == 0
      && length(azurerm_role_assignment.api_key_reader) == 0
      && output.openai_api_key_secret_id == ""
    )
    error_message = "Entra-only mode must not read Key Vault or create a key secret, secret-reader grants or a secret URI."
  }

  assert {
    condition = alltrue([for assignment in azurerm_role_assignment.inference :
      assignment.role_definition_name == "Cognitive Services OpenAI User"
    ])
    error_message = "Both workspace groups must use Cognitive Services OpenAI User, not a custom or higher-privilege role."
  }

  assert {
    condition = (
      toset(keys(azurerm_role_assignment.inference)) == toset(["owners", "researchers"])
      && azurerm_role_assignment.inference["owners"].principal_id == var.workspace_owners_group_id
      && azurerm_role_assignment.inference["researchers"].principal_id == var.workspace_researchers_group_id
      && alltrue([for assignment in azurerm_role_assignment.inference : assignment.principal_type == "Group" && assignment.scope == azurerm_cognitive_account.ai_foundry.id])
    )
    error_message = "Only the parent workspace data groups receive model access."
  }
}

# These mocks check module wiring. Real provider null preservation and destroy
# behaviour also need provider validation and lifecycle tests.
run "initial_entra_null_key" {
  command = apply

  override_resource {
    target = azurerm_cognitive_account.ai_foundry
    values = {
      id                 = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/rg-test/providers/Microsoft.CognitiveServices/accounts/aif-test"
      primary_access_key = null
    }
  }

  assert {
    condition = (
      !azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && azurerm_cognitive_account.ai_foundry.primary_access_key == null
      && length(azurerm_key_vault_secret.openai_api_key) == 0
      && length(azurerm_role_assignment.api_key_reader) == 0
    )
    error_message = "The first Entra-only installation must have a null key and no secret or reader grants."
  }
}

run "first_enable_plan" {
  command = plan
  variables {
    local_auth_enabled = true
  }

  assert {
    condition = (
      azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && length(azurerm_key_vault_secret.openai_api_key) == 1
      && length(azurerm_role_assignment.api_key_reader) == 2
    )
    error_message = "The first key-enabled plan must create one secret and two reader grants."
  }
}

run "private_api_key" {
  command = apply
  variables {
    local_auth_enabled = true
  }

  assert {
    condition = (
      azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && !azurerm_cognitive_account.ai_foundry.public_network_access_enabled
      && one(azurerm_cognitive_account.ai_foundry.network_acls).default_action == "Deny"
      && azurerm_private_endpoint.ai_foundry.private_service_connection[0].private_connection_resource_id == azurerm_cognitive_account.ai_foundry.id
    )
    error_message = "API keys must work independently of public access and retain the private endpoint."
  }

  assert {
    condition = (
      length(azurerm_key_vault_secret.openai_api_key) == 1
      && azurerm_key_vault_secret.openai_api_key[0].key_vault_id == data.azurerm_key_vault.ws[0].id
      && azurerm_key_vault_secret.openai_api_key[0].value == "synthetic-key-from-account-lookup"
      && output.openai_api_key_secret_id == azurerm_key_vault_secret.openai_api_key[0].versionless_id
    )
    error_message = "Store the account key in the workspace Key Vault and output only its versionless secret URI."
  }

  assert {
    condition = (
      toset(keys(azurerm_role_assignment.api_key_reader)) == toset(["owners", "researchers"])
      && alltrue([for name, assignment in azurerm_role_assignment.api_key_reader :
        assignment.scope == azurerm_key_vault_secret.openai_api_key[0].resource_versionless_id
        && assignment.role_definition_name == "Key Vault Secrets User"
        && assignment.principal_type == "Group"
        && assignment.principal_id == azurerm_role_assignment.inference[name].principal_id
      ])
      && alltrue([for assignment in azurerm_role_assignment.inference :
        assignment.role_definition_name == "Cognitive Services OpenAI User"
      ])
    )
    error_message = "Grant both workspace groups read access to this secret only, without changing their model-access role."
  }
}

run "disable_api_key" {
  command = apply

  assert {
    condition = (
      !azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && length(azurerm_key_vault_secret.openai_api_key) == 0
      && length(azurerm_role_assignment.api_key_reader) == 0
      && output.openai_api_key_secret_id == ""
      && length(azurerm_role_assignment.inference) == 2
    )
    error_message = "Disabling keys must remove the secret and its grants while retaining Entra access."
  }
}

run "reenable_api_key" {
  command = apply
  variables {
    local_auth_enabled = true
  }

  assert {
    condition = (
      azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && length(azurerm_key_vault_secret.openai_api_key) == 1
      && length(azurerm_role_assignment.api_key_reader) == 2
      && azurerm_key_vault_secret.openai_api_key[0].value == "synthetic-key-from-account-lookup"
      && output.openai_api_key_secret_id != ""
    )
    error_message = "Re-enabling keys must restore the secret, reader grants and secret URI."
  }
}

run "public_entra_only" {
  command = apply
  variables {
    is_exposed_externally = true
  }

  assert {
    condition = (
      azurerm_cognitive_account.ai_foundry.public_network_access_enabled
      && !azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && one(azurerm_cognitive_account.ai_foundry.network_acls).default_action == "Allow"
      && azurerm_private_endpoint.ai_foundry.private_service_connection[0].private_connection_resource_id == azurerm_cognitive_account.ai_foundry.id
      && length(azurerm_key_vault_secret.openai_api_key) == 0
      && length(azurerm_role_assignment.api_key_reader) == 0
      && output.openai_api_key_secret_id == ""
    )
    error_message = "Public mode must permit network access without requiring API keys or removing the private endpoint."
  }
}

run "public_api_key" {
  command = apply
  variables {
    is_exposed_externally = true
    local_auth_enabled    = true
  }

  assert {
    condition = (
      azurerm_cognitive_account.ai_foundry.public_network_access_enabled
      && azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && one(azurerm_cognitive_account.ai_foundry.network_acls).default_action == "Allow"
      && one(azurerm_cognitive_account.ai_foundry.network_acls).bypass == "None"
      && azurerm_cognitive_account.ai_foundry.outbound_network_access_restricted
      && toset(azurerm_cognitive_account.ai_foundry.fqdns) == toset(["deny-all.invalid"])
      && length(azurerm_role_assignment.inference) == 2
      && length(azurerm_role_assignment.api_key_reader) == 2
    )
    error_message = "Public access and keys must coexist with Entra access and retain the account's outbound restrictions."
  }
}

run "return_to_private_entra_only" {
  command = apply

  assert {
    condition = (
      !azurerm_cognitive_account.ai_foundry.public_network_access_enabled
      && !azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && one(azurerm_cognitive_account.ai_foundry.network_acls).default_action == "Deny"
      && azurerm_private_endpoint.ai_foundry.private_service_connection[0].private_connection_resource_id == azurerm_cognitive_account.ai_foundry.id
      && length(azurerm_key_vault_secret.openai_api_key) == 0
      && length(azurerm_role_assignment.api_key_reader) == 0
      && output.openai_api_key_secret_id == ""
    )
    error_message = "Returning to private Entra-only mode must remove key access and close public access without removing the private endpoint."
  }
}

run "reject_missing_workspace_groups" {
  command = plan
  variables {
    workspace_owners_group_id      = ""
    workspace_researchers_group_id = ""
  }
  expect_failures = [azurerm_role_assignment.inference]
}

run "reject_unapproved_model" {
  command = plan
  variables {
    openai_model = "unapproved-model | 1"
  }
  expect_failures = [var.openai_model]
}

run "reject_excess_capacity" {
  command = plan
  variables {
    openai_model_capacity = 101
  }
  expect_failures = [var.openai_model_capacity]
}

run "reject_fractional_capacity" {
  command = plan
  variables {
    openai_model_capacity = 1.5
  }
  expect_failures = [var.openai_model_capacity]
}

# Terraform automatically destroys each separate state after its final run.
run "destroy_keys_enabled" {
  command   = apply
  state_key = "destroy_keys_enabled"
  variables {
    local_auth_enabled = true
  }

  assert {
    condition = (
      azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && length(azurerm_key_vault_secret.openai_api_key) == 1
      && length(azurerm_role_assignment.api_key_reader) == 2
    )
    error_message = "Key-enabled teardown must start with the account, secret and both reader grants."
  }
}

run "destroy_entra_only" {
  command   = apply
  state_key = "destroy_entra_only"

  assert {
    condition = (
      !azurerm_cognitive_account.ai_foundry.local_auth_enabled
      && length(azurerm_key_vault_secret.openai_api_key) == 0
      && length(azurerm_role_assignment.api_key_reader) == 0
    )
    error_message = "Entra-only teardown must start without a secret or reader grants."
  }
}
