resource "terraform_data" "avd_registration" {
  triggers_replace = timestamp()

  provisioner "local-exec" {
    command = "bash ${path.module}/ensure_registration.sh"
    environment = {
      RP_CLIENT_ID    = data.azurerm_user_assigned_identity.resource_processor_vmss_id.client_id
      HOST_POOL_ID    = data.azurerm_virtual_desktop_host_pool.avd.id
      STORAGE_ACCOUNT = data.azurerm_storage_account.stg.name
      LOCK_CONTAINER  = "avd-registration-${local.short_parent_id}"
      KEY_VAULT_NAME  = data.azurerm_key_vault.ws.name
      SECRET_NAME     = "avd-registration-token-${local.short_parent_id}"
    }
  }

  depends_on = [azapi_resource_action.restart_session_host, terraform_data.avd_dsc]
}

resource "azurerm_storage_container" "avd_artifacts" {
  name                  = "avdur-${local.short_service_id}"
  storage_account_id    = data.azurerm_storage_account.stg.id
  container_access_type = "private"
}

resource "terraform_data" "avd_dsc" {
  triggers_replace = [local.avd_dsc_artifact_sha256, local.avd_dsc_artifact_url]

  provisioner "local-exec" {
    interpreter = ["/bin/sh", "-c"]
    command     = <<-EOT
      token_response=$(curl --fail --silent --show-error -H Metadata:true "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fstorage.azure.com%2F&client_id=${data.azurerm_user_assigned_identity.resource_processor_vmss_id.client_id}")
      access_token=$(printf '%s' "$token_response" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
      test -n "$access_token"
      curl --fail-with-body --silent --show-error --retry 18 --retry-delay 10 --retry-all-errors \
        --request PUT \
        --header "Authorization: Bearer $access_token" \
        --header "x-ms-version: 2023-11-03" \
        --header "x-ms-date: $(LC_ALL=C date -u '+%a, %d %b %Y %H:%M:%S GMT')" \
        --header "x-ms-blob-type: BlockBlob" \
        --upload-file "${path.module}/../Configuration.zip" \
        "${data.azurerm_storage_account.stg.primary_blob_endpoint}${azurerm_storage_container.avd_artifacts.name}/Configuration.zip"
    EOT
  }
}

resource "azurerm_network_interface" "sessionhost" {
  name                = "nic-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  tags                = local.tre_user_resources_tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = data.azurerm_subnet.services.id
    private_ip_address_allocation = "Dynamic"
  }

  lifecycle {
    ignore_changes = [tags]

    precondition {
      condition     = data.azurerm_virtual_desktop_host_pool.avd.type == "Personal"
      error_message = "Personal session-host user resources can only be deployed under a Personal AVD host pool."
    }
  }
}

resource "random_password" "password" {
  length           = 16
  lower            = true
  min_lower        = 1
  upper            = true
  min_upper        = 1
  numeric          = true
  min_numeric      = 1
  special          = true
  min_special      = 1
  override_special = "_%@"
}

resource "azurerm_windows_virtual_machine" "sessionhost" {
  name                       = local.vm_name
  location                   = data.azurerm_resource_group.ws.location
  resource_group_name        = data.azurerm_resource_group.ws.name
  network_interface_ids      = [azurerm_network_interface.sessionhost.id]
  size                       = local.vm_sizes[var.vm_size]
  allow_extension_operations = true
  admin_username             = local.admin_username
  admin_password             = random_password.password.result
  encryption_at_host_enabled = true
  secure_boot_enabled        = local.secure_boot_enabled
  vtpm_enabled               = local.vtpm_enabled
  license_type               = "Windows_Client"

  dynamic "source_image_reference" {
    for_each = local.selected_image_source_refs
    content {
      publisher = source_image_reference.value["publisher"]
      offer     = source_image_reference.value["offer"]
      sku       = source_image_reference.value["sku"]
      version   = source_image_reference.value["version"]
    }
  }

  os_disk {
    name                 = "osdisk-${local.vm_name}"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags, secure_boot_enabled, vtpm_enabled, admin_username, os_disk[0].storage_account_type] }
}

resource "azurerm_role_assignment" "session_host_login" {
  scope                = azurerm_windows_virtual_machine.sessionhost.id
  role_definition_name = "Virtual Machine User Login"
  principal_id         = var.owner_id
}

resource "azurerm_role_assignment" "session_host_power_on" {
  scope                = azurerm_windows_virtual_machine.sessionhost.id
  role_definition_name = "Desktop Virtualization Power On Contributor"
  principal_id         = data.azuread_service_principal.avd.object_id
}

resource "azurerm_role_assignment" "session_host_avd_artifact_reader" {
  scope                = "${data.azurerm_storage_account.stg.id}/blobServices/default/containers/${azurerm_storage_container.avd_artifacts.name}"
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_windows_virtual_machine.sessionhost.identity[0].principal_id
}

# AVD Agent extension to join the session host to the host pool
resource "azurerm_virtual_machine_run_command" "prepare_session_host" {
  name               = "prepare-avd-session-host"
  location           = data.azurerm_resource_group.ws.location
  virtual_machine_id = azurerm_windows_virtual_machine.sessionhost.id

  source {
    script = templatefile("${path.module}/prepare_session_host.ps1.tftpl", {
      clipboard_server_to_client = local.clipboard_server_to_client
      clipboard_client_to_server = local.clipboard_client_to_server
    })
  }
}

resource "azapi_resource_action" "restart_session_host" {
  type        = "Microsoft.Compute/virtualMachines@2024-07-01"
  resource_id = azurerm_windows_virtual_machine.sessionhost.id
  action      = "restart"

  depends_on = [azurerm_virtual_machine_run_command.prepare_session_host]
  lifecycle {
    replace_triggered_by = [azurerm_virtual_machine_run_command.prepare_session_host]
  }
}

resource "azurerm_virtual_machine_extension" "avd_dsc" {
  name                       = "configure-avd-session-host"
  virtual_machine_id         = azurerm_windows_virtual_machine.sessionhost.id
  publisher                  = "Microsoft.Compute"
  type                       = "CustomScriptExtension"
  type_handler_version       = "1.10"
  auto_upgrade_minor_version = true
  tags                       = local.tre_user_resources_tags

  protected_settings = jsonencode({
    commandToExecute = "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"& ([scriptblock]::Create([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('${base64encode(templatefile("${path.module}/configure_session_host.ps1.tftpl", {
      artifact_url               = local.avd_dsc_artifact_url
      artifact_sha256            = local.avd_dsc_artifact_sha256
      host_pool_name             = data.azurerm_virtual_desktop_host_pool.avd.name
      registration_token         = data.azurerm_key_vault_secret.avd_registration_token.value
      clipboard_server_to_client = local.clipboard_server_to_client
      clipboard_client_to_server = local.clipboard_client_to_server
      mount_storage_command      = local.mount_storage_command
    }))}'))))\""
  })

  lifecycle {
    ignore_changes = [tags]

    precondition {
      condition     = !contains(["client_to_session", "session_to_client"], data.azurerm_key_vault_secret.clipboard_transfer_direction.value) || contains(["Windows 11 Multi-Session", "Windows 11 Enterprise"], var.image)
      error_message = "One-way clipboard redirection requires a supported Windows 11 Enterprise image. Replace legacy desktops before enabling directional clipboard access."
    }
  }

  depends_on = [
    azapi_resource_action.restart_session_host,
    azurerm_role_assignment.session_host_avd_artifact_reader,
    terraform_data.avd_dsc,
  ]
}

resource "azapi_resource_action" "session_host_assignment" {
  type        = "Microsoft.DesktopVirtualization/hostPools/sessionHosts@2022-02-10-preview"
  resource_id = "${data.azurerm_virtual_desktop_host_pool.avd.id}/sessionHosts/${local.vm_name}"
  action      = ""
  method      = "PATCH"

  body = {
    properties = {
      assignedUser = local.owner_user_principal_name
      friendlyName = coalesce(trimspace(var.display_name), local.vm_name)
    }
  }

  retry = {
    error_message_regex  = ["(?i)(not found|404)"]
    interval_seconds     = 10
    max_interval_seconds = 60
  }

  depends_on = [azurerm_virtual_machine_extension.avd_dsc]

  lifecycle {
    replace_triggered_by = [azurerm_windows_virtual_machine.sessionhost.virtual_machine_id]
  }
}

resource "azapi_resource_action" "unregister_session_host" {
  type             = "Microsoft.DesktopVirtualization/hostPools/sessionHosts@2024-04-03"
  resource_id      = "${data.azurerm_virtual_desktop_host_pool.avd.id}/sessionHosts/${local.vm_name}"
  method           = "DELETE"
  when             = "destroy"
  ignore_not_found = true
  query_parameters = { force = ["true"] }

  depends_on = [azapi_resource_action.session_host_assignment, azurerm_virtual_machine_extension.aad_join]

  lifecycle {
    replace_triggered_by = [azurerm_windows_virtual_machine.sessionhost.virtual_machine_id]
  }
}

# AAD Join extension for Microsoft Entra ID authentication
resource "azurerm_virtual_machine_extension" "aad_join" {
  name                       = "AADLoginForWindows"
  virtual_machine_id         = azurerm_windows_virtual_machine.sessionhost.id
  publisher                  = "Microsoft.Azure.ActiveDirectory"
  type                       = "AADLoginForWindows"
  type_handler_version       = "2.2"
  auto_upgrade_minor_version = true
  tags                       = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }

  depends_on = [azapi_resource_action.session_host_assignment]
}

resource "azurerm_key_vault_secret" "sessionhost_password" {
  name         = local.vm_password_secret_name
  value        = "${local.admin_username}\n${random_password.password.result}"
  key_vault_id = data.azurerm_key_vault.ws.id
  tags         = local.tre_user_resources_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_dev_test_global_vm_shutdown_schedule" "shutdown_schedule" {
  count = var.enable_shutdown_schedule ? 1 : 0

  location              = data.azurerm_resource_group.ws.location
  virtual_machine_id    = azurerm_windows_virtual_machine.sessionhost.id
  daily_recurrence_time = var.shutdown_time
  timezone              = var.shutdown_timezone
  enabled               = var.enable_shutdown_schedule
  notification_settings {
    enabled = false
  }
}
