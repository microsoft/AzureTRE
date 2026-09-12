resource "terraform_data" "clipboard_policy" {
  input = local.clipboard_transfer_direction

  lifecycle { ignore_changes = [input] }
}

resource "azurerm_virtual_desktop_host_pool" "avd" {
  name                             = local.hostpool_name
  location                         = data.azurerm_resource_group.ws.location
  resource_group_name              = data.azurerm_resource_group.ws.name
  friendly_name                    = local.hostpool_friendly_name
  description                      = "${var.host_pool_type} host pool for secure virtual desktop access"
  type                             = var.host_pool_type
  load_balancer_type               = var.host_pool_type == "Personal" ? "Persistent" : "BreadthFirst"
  personal_desktop_assignment_type = var.host_pool_type == "Personal" ? "Direct" : null
  maximum_sessions_allowed         = var.host_pool_type == "Pooled" ? var.maximum_sessions : null
  start_vm_on_connect              = true
  public_network_access            = "EnabledForClientsOnly"
  custom_rdp_properties            = "${local.authentication_rdp_properties}${local.restricted_redirection_rdp_properties}${local.clipboard_rdp_property}"
  tags                             = local.workspace_service_tags

  lifecycle {
    ignore_changes = [tags, load_balancer_type]
    precondition {
      condition     = terraform_data.clipboard_policy.output == local.clipboard_transfer_direction
      error_message = "Clipboard direction is fixed at service creation. Create a new AVD service to change it safely for all session hosts."
    }
  }
}

resource "azapi_resource_action" "multiple_personal_desktops" {
  count = var.host_pool_type == "Personal" ? 1 : 0

  type        = "Microsoft.DesktopVirtualization/hostPools@2025-10-10"
  resource_id = azurerm_virtual_desktop_host_pool.avd.id
  method      = "PATCH"
  body = {
    properties = { loadBalancerType = "MultiplePersistent" }
  }

  lifecycle {
    replace_triggered_by = [azurerm_virtual_desktop_host_pool.avd]
  }
}

resource "azurerm_storage_container" "avd_registration" {
  name                  = "avd-registration-${local.short_service_id}"
  storage_account_id    = data.azurerm_storage_account.stg.id
  container_access_type = "private"

}

resource "terraform_data" "avd_registration" {
  triggers_replace = timestamp()

  provisioner "local-exec" {
    command = "bash ${path.module}/ensure_registration.sh"
    environment = {
      RP_CLIENT_ID    = data.azurerm_user_assigned_identity.resource_processor_vmss_id.client_id
      HOST_POOL_ID    = azurerm_virtual_desktop_host_pool.avd.id
      STORAGE_ACCOUNT = data.azurerm_storage_account.stg.name
      LOCK_CONTAINER  = azurerm_storage_container.avd_registration.name
      KEY_VAULT_NAME  = data.azurerm_key_vault.ws.name
      SECRET_NAME     = "avd-registration-token-${local.short_service_id}"
    }
  }

  depends_on = [azapi_resource_action.restart_pooled_session_host, terraform_data.avd_dsc]
}

data "azurerm_key_vault_secret" "avd_registration_token" {
  name         = "avd-registration-token-${local.short_service_id}"
  key_vault_id = data.azurerm_key_vault.ws.id
  depends_on   = [terraform_data.avd_registration]
}

resource "azurerm_key_vault_secret" "clipboard_transfer_direction" {
  name         = "avd-clipboard-direction-${local.short_service_id}"
  value        = local.clipboard_transfer_direction
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

# Azure Virtual Desktop Workspace
resource "azurerm_virtual_desktop_workspace" "avd" {
  name                = local.avd_workspace_name
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  friendly_name       = local.workspace_friendly_name
  description         = "Secure virtual desktop workspace for TRE"
  tags                = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

# Desktop Application Group (required for personal desktop access)
resource "azurerm_virtual_desktop_application_group" "avd" {
  name                         = local.application_group_name
  location                     = data.azurerm_resource_group.ws.location
  resource_group_name          = data.azurerm_resource_group.ws.name
  host_pool_id                 = azurerm_virtual_desktop_host_pool.avd.id
  type                         = "Desktop"
  friendly_name                = local.app_group_friendly_name
  default_desktop_display_name = local.app_group_friendly_name
  description                  = "Desktop application group for personal desktops"
  tags                         = local.workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

# Associate application group with workspace
resource "azurerm_virtual_desktop_workspace_application_group_association" "avd" {
  workspace_id         = azurerm_virtual_desktop_workspace.avd.id
  application_group_id = azurerm_virtual_desktop_application_group.avd.id
}

resource "azurerm_role_assignment" "workspace_users" {
  for_each = local.workspace_role_principal_ids

  scope                = azurerm_virtual_desktop_application_group.avd.id
  role_definition_name = "Desktop Virtualization User"
  principal_id         = each.value
}

# Diagnostic settings for host pool
resource "azurerm_monitor_diagnostic_setting" "hostpool" {
  name                       = "diag-${local.hostpool_name}"
  target_resource_id         = azurerm_virtual_desktop_host_pool.avd.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  enabled_log {
    category = "Checkpoint"
  }

  enabled_log {
    category = "Error"
  }

  enabled_log {
    category = "Management"
  }

  enabled_log {
    category = "Connection"
  }

  enabled_log {
    category = "HostRegistration"
  }

  enabled_log {
    category = "AgentHealthStatus"
  }

  enabled_log {
    category = "NetworkData"
  }

  enabled_log {
    category = "SessionHostManagement"
  }
}

# Diagnostic settings for workspace
resource "azurerm_monitor_diagnostic_setting" "workspace" {
  name                       = "diag-${local.avd_workspace_name}"
  target_resource_id         = azurerm_virtual_desktop_workspace.avd.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  enabled_log {
    category = "Checkpoint"
  }

  enabled_log {
    category = "Error"
  }

  enabled_log {
    category = "Management"
  }

  enabled_log {
    category = "Feed"
  }
}

# Diagnostic settings for application group
resource "azurerm_monitor_diagnostic_setting" "application_group" {
  name                       = "diag-${local.application_group_name}"
  target_resource_id         = azurerm_virtual_desktop_application_group.avd.id
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.tre.id

  enabled_log {
    category = "Checkpoint"
  }

  enabled_log {
    category = "Error"
  }

  enabled_log {
    category = "Management"
  }
}
