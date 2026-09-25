# Retry the purge if Azure still reports a deleted account as busy.
# Only this service's account is targeted.
resource "azapi_resource_action" "purge_ai_foundry" {
  type = "Microsoft.CognitiveServices/locations/resourceGroups/deletedAccounts@2024-10-01"
  resource_id = join("", [
    "/subscriptions/", local.workspace_subscription_id,
    "/providers/Microsoft.CognitiveServices/locations/", data.azurerm_resource_group.ws.location,
    "/resourceGroups/", data.azurerm_resource_group.ws.name,
    "/deletedAccounts/aif-", local.service_resource_name_suffix
  ])
  method           = "DELETE"
  when             = "destroy"
  ignore_not_found = true

  retry = {
    error_message_regex = [
      "(?i)RequestConflict",
      "(?i)provisioning state is not terminal"
    ]
    interval_seconds     = 30
    max_interval_seconds = 120
  }

  timeouts {
    delete = "30m"
  }
}

resource "azurerm_cognitive_account" "ai_foundry" {
  name                          = "aif-${local.service_resource_name_suffix}"
  location                      = data.azurerm_resource_group.ws.location
  resource_group_name           = data.azurerm_resource_group.ws.name
  kind                          = "AIServices"
  sku_name                      = "S0"
  custom_subdomain_name         = "aif-${local.service_resource_name_suffix}"
  public_network_access_enabled = var.is_exposed_externally
  local_auth_enabled            = var.local_auth_enabled
  project_management_enabled    = true

  # Model-only use needs no service-initiated requests to external hosts.
  # A reserved, non-resolving sentinel keeps deny-all enforcement active.
  # Retain the empty-list live regression checks before removing this workaround.
  # https://learn.microsoft.com/azure/ai-services/cognitive-services-data-loss-prevention
  outbound_network_access_restricted = true
  fqdns                              = ["deny-all.invalid"]

  identity {
    type = "SystemAssigned"
  }

  network_acls {
    default_action = var.is_exposed_externally ? "Allow" : "Deny"
    bypass         = "None"
  }

  tags = local.workspace_service_tags

  timeouts {
    create = "60m"
    update = "60m"
    delete = "30m"
    read   = "5m"
  }

  lifecycle {
    ignore_changes = [tags]
  }

  depends_on = [azapi_resource_action.purge_ai_foundry]
}

# AzureRM can return before Azure finishes an AIServices account that has
# project_management_enabled set to true. Wait before creating dependent
# resources.
resource "time_sleep" "wait_for_ai_foundry" {
  depends_on      = [azurerm_cognitive_account.ai_foundry]
  create_duration = "600s" # 10 minutes

  triggers = {
    account_id = azurerm_cognitive_account.ai_foundry.id
  }
}

# A private endpoint gives AI Foundry a private network address in the workspace.
resource "azurerm_private_endpoint" "ai_foundry" {
  name                = "pe-aif-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    name                           = "psc-aif-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_cognitive_account.ai_foundry.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  depends_on = [time_sleep.wait_for_ai_foundry]

  private_dns_zone_group {
    name = "dns-aif-${local.service_resource_name_suffix}"
    private_dns_zone_ids = [
      data.azurerm_private_dns_zone.cognitive_services.id,
      data.azurerm_private_dns_zone.openai.id,
      data.azurerm_private_dns_zone.ai_services.id
    ]
  }

  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
    read   = "5m"
  }

  lifecycle {
    ignore_changes = [tags]
  }
}

# Keep one default project within this Foundry account.
# Researcher permissions are limited to the account-level OpenAI API.
resource "azurerm_cognitive_account_project" "default" {
  name                 = "default"
  cognitive_account_id = azurerm_cognitive_account.ai_foundry.id
  location             = data.azurerm_resource_group.ws.location
  display_name         = "Default Project"
  tags                 = local.workspace_service_tags

  identity {
    type = "SystemAssigned"
  }

  lifecycle {
    ignore_changes = [tags]
  }

  # AzureRM 4.81.0 does not lock project operations against other account children.
  # Serialise these operations, and delete the project before the model.
  # https://github.com/hashicorp/terraform-provider-azurerm/pull/33151
  depends_on = [
    azurerm_private_endpoint.ai_foundry,
    azurerm_cognitive_deployment.openai
  ]

  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
    read   = "5m"
  }
}
# Ask Azure which models and pricing tiers are available for this account and
# region. Availability can change after this template is published.
data "azapi_resource_action" "available_models" {
  type                   = "Microsoft.CognitiveServices/accounts@2025-06-01"
  resource_id            = azurerm_cognitive_account.ai_foundry.id
  action                 = "models"
  method                 = "GET"
  response_export_values = ["value"]

  depends_on = [time_sleep.wait_for_ai_foundry]
}

# Deploy the OpenAI model.
resource "azurerm_cognitive_deployment" "openai" {
  # Include the model version in the name. The create_before_destroy setting can
  # then keep the active model until Azure creates its replacement.
  name                   = replace("${local.openai_model.name}-${local.openai_model.version}", ".", "-")
  cognitive_account_id   = azurerm_cognitive_account.ai_foundry.id
  version_upgrade_option = "NoAutoUpgrade"

  model {
    format  = "OpenAI"
    name    = local.openai_model.name
    version = local.openai_model.version
  }

  sku {
    name     = "Standard"
    capacity = var.openai_model_capacity
  }

  timeouts {
    create = "30m"
    update = "30m"
    delete = "30m"
    read   = "5m"
  }

  lifecycle {
    create_before_destroy = true

    precondition {
      condition     = local.selected_openai_model_is_deployable
      error_message = "Azure cannot deploy the OpenAI model '${var.openai_model}' with the Standard pricing tier in this account and region. Select a model that the current template supports, then retry."
    }
  }
}
